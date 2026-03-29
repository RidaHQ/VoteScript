import time
import random
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from core.tor_manager import TorManager
from browser.fingerprint import FingerprintManager
from browser.human_behavior import HumanBehavior
from strategies.history import RandomHistory
from strategies.block_handler import BlockHandler

logger = logging.getLogger(__name__)

class Voter:
    def __init__(self, config):
        self.config = config
        self.tor = TorManager(config['tor_proxy'], config['tor_control_port'])
        self.fingerprint = FingerprintManager(config)
        self.block_handler = BlockHandler()
        self.driver = None
        self.user_profile = self._select_profile()
        
    def _select_profile(self):
        profiles_config = self.config.get('user_profiles', {})
        if not profiles_config.get('active', False):
            return None
        types = profiles_config.get('types', [])
        if not types:
            return None
        probabilities = [t.get('probability', 0) for t in types]
        return random.choices(types, weights=probabilities)[0]
        
    def setup_browser(self):
        options = Options()
        options.add_argument("--headless")
        proxy_host, proxy_port = self.config['tor_proxy'].split(':')
        options.set_preference('network.proxy.type', 1)
        options.set_preference('network.proxy.socks', proxy_host)
        options.set_preference('network.proxy.socks_port', int(proxy_port))
        options.set_preference('network.proxy.socks_remote_dns', True)
        fingerprint = self.fingerprint.generate()
        options = self.fingerprint.apply(options, fingerprint)
        width, height = map(int, fingerprint['resolution'].split(','))
        try:
            service = Service(executable_path=self.config['geckodriver_path'])
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.set_window_size(width, height)
            logger.info(f"Browser {width}x{height}")
            return True
        except Exception as e:
            logger.error(f"Browser error: {e}")
            return False
    
    def handle_language_popup(self):
        try:
            time.sleep(2)
            try:
                alert = self.driver.switch_to.alert
                logger.info("Language popup accepted")
                alert.accept()
                time.sleep(1)
                return True
            except:
                pass
        except:
            pass
        return False
    
    def get_page_title(self):
        try:
            wait = WebDriverWait(self.driver, 3)
            title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.singleTitle")))
            title = title_element.text.strip()
            if title:
                return title[:35] + "..." if len(title) > 35 else title
            return None
        except:
            return None
    
    def check_block(self):
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, "div.alert.alert-warning")
            if "Voting for this suggestion is temporarily disabled" in element.text:
                logger.warning("Block detected")
                return True
        except NoSuchElementException:
            pass
        return False
    
    def find_vote_button(self):
        selectors = [
            (By.XPATH, "//button[contains(@class, 'btn-voting-panel')]"),
            (By.XPATH, "//button[contains(., 'Voted up')]"),
        ]
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    return elements[0]
            except:
                continue
        return None
    
    def get_vote_count(self):
        try:
            vote_element = self.driver.find_element(By.CSS_SELECTOR, "span.vote-count")
            vote_count = vote_element.get_attribute("data-vote-count")
            if vote_count:
                return int(vote_count)
            return int(vote_element.text.strip())
        except:
            return None
    
    def vote_single_link(self, link, idx, total, stop_event=None, vote_callback=None, 
                         block_callback=None, title_callback=None, pause_event=None):
        try:
            while pause_event and pause_event.is_set():
                time.sleep(0.5)
                if stop_event and stop_event.is_set():
                    return False, None
            if stop_event and stop_event.is_set():
                return False, None
                
            self.driver.get(link)
            time.sleep(random.uniform(4, 8))
            
            while pause_event and pause_event.is_set():
                time.sleep(0.5)
                if stop_event and stop_event.is_set():
                    return False, None
            if stop_event and stop_event.is_set():
                return False, None
                
            self.handle_language_popup()
            
            title = self.get_page_title()
            if title and title_callback:
                title_callback(link, title, idx)
            
            if self.check_block():
                logger.warning(f"Link #{idx} BLOCKED")
                if block_callback:
                    block_callback(link, True)
                return False, None
            else:
                if block_callback:
                    block_callback(link, False)
            
            votes_before = self.get_vote_count()
            if votes_before is not None:
                logger.info(f"Votes before: {votes_before}")
            
            logger.info(f"Waiting...")
            
            button = None
            attempts = 0
            while attempts < 10:
                while pause_event and pause_event.is_set():
                    time.sleep(0.5)
                    if stop_event and stop_event.is_set():
                        return False, None
                if stop_event and stop_event.is_set():
                    return False, None
                button = self.find_vote_button()
                if button:
                    break
                time.sleep(1)
                attempts += 1
            
            if button:
                human = HumanBehavior(self.driver, self.config)
                human.mouse_movement(button)
                logger.info("Vote registered")
                time.sleep(2)
                votes_after = self.get_vote_count()
                if votes_after is not None:
                    logger.info(f"Votes after: {votes_after}")
                    if vote_callback:
                        vote_callback(link, votes_before, votes_after)
                return True, votes_after
            else:
                logger.warning("Button not found")
                return False, None
                
        except Exception as e:
            logger.error(f"Error: {e}")
            return False, None
    
    def vote_all_links(self, stop_event=None, vote_callback=None, block_callback=None, 
                       ip_callback=None, title_callback=None, pause_event=None, 
                       history_active=True, link_toggle_states=None):
        logger.info("NEW IP")
        
        max_ip_attempts = 3
        ip_changed = False
        
        for attempt in range(max_ip_attempts):
            while pause_event and pause_event.is_set():
                time.sleep(0.5)
                if stop_event and stop_event.is_set():
                    return 0
            if stop_event and stop_event.is_set():
                return 0
            logger.info(f"IP change attempt {attempt+1}/{max_ip_attempts}")
            ip_changed = self.tor.change_ip(callback=ip_callback)
            if ip_changed:
                logger.info("IP changed successfully")
                break
            else:
                if attempt < max_ip_attempts - 1:
                    pause = 5 * (attempt + 1)
                    logger.info(f"Waiting {pause}s before retry...")
                    time.sleep(pause)
        
        if not ip_changed:
            logger.warning("IP change failed after all attempts, continuing with current IP")
            os._exit(1)
            
        try:
            while pause_event and pause_event.is_set():
                time.sleep(0.5)
                if stop_event and stop_event.is_set():
                    return 0
            if stop_event and stop_event.is_set():
                return 0
            if not self.setup_browser():
                return 0
            if history_active and random.random() < 0.8 and (not stop_event or not stop_event.is_set()):
                history = RandomHistory(self.driver, self.config)
                history.navigate(stop_event, pause_event)
            
            all_links = self.config['target_urls'].copy()
            logger.info(f"{len(all_links)} links to vote")
            
            successes = 0
            
            for idx, link in enumerate(all_links, 1):
                if link_toggle_states and not link_toggle_states.get(link, True):
                    logger.info(f"  [{idx}/{len(all_links)}] Link disabled, skipping")
                    continue
                while pause_event and pause_event.is_set():
                    time.sleep(0.5)
                    if stop_event and stop_event.is_set():
                        logger.info("Stop requested, stopping voting")
                        break
                if stop_event and stop_event.is_set():
                    logger.info("Stop requested, stopping voting")
                    break
                logger.info(f"  [{idx}/{len(all_links)}]")
                success, votes_after = self.vote_single_link(
                    link, idx, len(all_links), stop_event, 
                    vote_callback, block_callback, title_callback, pause_event
                )
                if success:
                    successes += 1
                if idx < len(all_links) and (not stop_event or not stop_event.is_set()):
                    pause = random.uniform(
                        self.config['limits']['pause_min_between_votes'],
                        self.config['limits']['pause_max_between_votes']
                    )
                    logger.info(f"Pause {pause:.0f}s")
                    for _ in range(int(pause)):
                        while pause_event and pause_event.is_set():
                            time.sleep(0.5)
                            if stop_event and stop_event.is_set():
                                break
                        if stop_event and stop_event.is_set():
                            break
                        time.sleep(1)
            logger.info(f"IP completed: {successes}/{len(all_links)}")
            return successes
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None