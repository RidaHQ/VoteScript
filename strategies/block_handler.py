import time
import logging

logger = logging.getLogger(__name__)

class BlockHandler:
    def __init__(self):
        self.count = 0
        self.base_time = 60
    
    def handle(self):
        self.count += 1
        wait = min(self.base_time * (2 ** (self.count - 1)), 3600)
        logger.warning(f"Block #{self.count} - waiting {wait//60}min")
        time.sleep(wait)
        if self.count >= 3:
            return "change_ip"
        return "retry"
    
    def reset(self):
        self.count = 0