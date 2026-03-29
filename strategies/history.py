import time
import random
import logging
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class RandomHistory:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config['history']
    
    def navigate(self, stop_event=None, pause_event=None):
        """
        Perform random navigation with support for stop and pause
        """
        if not self.config.get('active', True):
            return
            
        logger.info("Navigation:")
        depth = random.randint(self.config['depth']['min'], self.config['depth']['max'])
        
        for i in range(depth):
            # Check stop
            if stop_event and stop_event.is_set():
                logger.info("Navigation interrupted")
                return
            
            # Check pause
            while pause_event and pause_event.is_set():
                time.sleep(0.5)
                if stop_event and stop_event.is_set():
                    return
                
            try:
                site = random.choice(self.config['sites'])
                logger.info(f"  {i+1}/{depth} - {site[:30]}...")
                
                self.driver.get(site)
                time.sleep(random.uniform(2, 4))
                
                # Check pause after load
                while pause_event and pause_event.is_set():
                    time.sleep(0.5)
                    if stop_event and stop_event.is_set():
                        return
                
                # Natural scroll
                try:
                    height = self.driver.execute_script("return document.body.scrollHeight")
                    if height > 100:
                        scrolls = random.randint(1, 2)
                        for _ in range(scrolls):
                            scroll = random.randint(100, min(height-100, 500))
                            self.driver.execute_script(f"window.scrollTo(0, {scroll});")
                            time.sleep(random.uniform(0.3, 1))
                except:
                    pass
                
                # Reading time
                duration = random.uniform(
                    self.config['time_per_site']['min'],
                    self.config['time_per_site']['max']
                )
                logger.info(f"  Reading: {duration:.0f}s")
                
                # Pause with checks
                for _ in range(int(duration)):
                    if stop_event and stop_event.is_set():
                        return
                    while pause_event and pause_event.is_set():
                        time.sleep(0.5)
                        if stop_event and stop_event.is_set():
                            return
                    time.sleep(1)
                
                # Pause between sites
                pause = random.uniform(2, 5)
                for _ in range(int(pause)):
                    if stop_event and stop_event.is_set():
                        return
                    while pause_event and pause_event.is_set():
                        time.sleep(0.5)
                        if stop_event and stop_event.is_set():
                            return
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"Navigation error: {e}")
                continue
        
        logger.info("Navigation completed")