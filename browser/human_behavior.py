import time
import random
import logging
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class HumanBehavior:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config['behavior']
        self.profile_config = config.get('user_profiles', {})
        self.profile = self._select_profile()
        
    def _select_profile(self):
        """Select user profile based on probability"""
        if not self.profile_config.get('active', False):
            return None
            
        types = self.profile_config.get('types', [])
        if not types:
            return None
            
        probabilities = [t.get('probability', 0) for t in types]
        return random.choices(types, weights=probabilities)[0]
    
    def _get_scroll_speed(self):
        """Return scroll parameters based on profile"""
        if not self.profile:
            return {'min': 0.3, 'max': 1.2}
            
        speed = self.profile.get('scroll_speed', 'medium')
        if speed == 'fast':
            return {'min': 0.1, 'max': 0.5}
        elif speed == 'slow':
            return {'min': 0.8, 'max': 2.0}
        else:
            return {'min': 0.3, 'max': 1.2}
    
    def _get_reading_time(self):
        """Return reading time based on profile"""
        if not self.profile:
            return {'min': 2, 'max': 5}
            
        time_value = self.profile.get('reading_time', 'medium')
        if time_value == 'short':
            return {'min': 1, 'max': 3}
        elif time_value == 'long':
            return {'min': 5, 'max': 10}
        else:
            return {'min': 2, 'max': 5}
    
    def natural_scroll(self):
        if not self.config.get('scroll', True):
            return
        try:
            height = self.driver.execute_script("return document.body.scrollHeight")
            viewport = self.driver.execute_script("return window.innerHeight")
            
            if height <= viewport:
                return
                
            pos = 0
            speed = self._get_scroll_speed()
            
            while pos < height - viewport:
                inc = random.randint(100, 300)
                pos = min(pos + inc, height - viewport)
                self.driver.execute_script(f"window.scrollTo(0, {pos});")
                
                pause = random.uniform(speed['min'], speed['max'])
                time.sleep(pause)
                
            if random.random() < 0.2:
                time.sleep(random.uniform(0.5, 1))
                self.driver.execute_script(f"window.scrollTo(0, {random.randint(0, pos)});")
                
        except Exception as e:
            logger.debug(f"Scroll error: {e}")
    
    def mouse_movement(self, element):
        """Realistic mouse movement towards element"""
        try:
            time.sleep(random.uniform(0.5, 1.5))
            
            position = element.location
            size = element.size
            
            click_precision = self.config.get('click_precision', {})
            max_offset = click_precision.get('max_offset', 5)
            
            target_x = position['x'] + size['width'] // 2 + random.randint(-max_offset, max_offset)
            target_y = position['y'] + size['height'] // 2 + random.randint(-max_offset, max_offset)
            
            actions = ActionChains(self.driver)
            actions.move_to_element(element)
            
            if self.config.get('mouse_tremor', False):
                for _ in range(random.randint(2, 5)):
                    actions.move_by_offset(
                        random.uniform(-2, 2),
                        random.uniform(-2, 2)
                    )
            
            actions.perform()
            
            if self.config.get('hesitation', False) and random.random() < 0.3:
                time.sleep(random.uniform(0.3, 1.0))
            
            try:
                element.click()
            except:
                self.driver.execute_script("arguments[0].click();", element)
                
        except Exception as e:
            logger.warning(f"Mouse movement error: {e}")
            try:
                self.driver.execute_script("arguments[0].click();", element)
            except:
                pass
    
    def random_error(self):
        """Simulate occasional human errors"""
        if not self.config.get('random_errors', False):
            return False
            
        probability = self.config.get('click_precision', {}).get('miss_click_probability', 0.03)
        
        if random.random() < probability:
            logger.info("Click outside target...")
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.click()
                time.sleep(random.uniform(0.5, 1.5))
            except:
                pass
            return True
            
        return False
    
    def reading_pause(self):
        """Pause to simulate reading"""
        time_value = self._get_reading_time()
        pause = random.uniform(time_value['min'], time_value['max'])
        logger.info(f"Reading: {pause:.1f}s")
        time.sleep(pause)