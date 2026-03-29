import time
import random
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class TemporalManager:
    def __init__(self, config):
        self.config = config['limits']
        self.pattern_config = config.get('temporal_patterns', {})
        self.votes_today = 0
        self.last_vote = None
        self.current_day = datetime.now().day
        self.last_vote_day = None
        
    def can_vote(self):
        """Check if can vote at this moment"""
        now = datetime.now()
        
        # Daily reset
        if now.day != self.current_day:
            self.votes_today = 0
            self.current_day = now.day
            logger.info(f"Daily reset: new day")
        
        # Daily limit check
        if self.votes_today >= self.config['max_votes_per_day']:
            logger.debug(f"Daily limit reached: {self.votes_today}/{self.config['max_votes_per_day']}")
            return False
        
        # Day of week check
        if not self._is_day_allowed(now):
            weekday = now.isoweekday()
            logger.debug(f"Day not allowed: {weekday}")
            return False
        
        # Time slot check with probability
        if not self._is_time_slot_allowed(now):
            logger.debug(f"Time slot not allowed: {now.hour}:{now.minute}")
            return False
        
        # Minimum pause between votes
        if self.last_vote:
            minutes_passed = (now - self.last_vote).seconds / 60
            if minutes_passed < 0.5:
                logger.debug(f"Minimum pause not respected: {minutes_passed*60:.0f}s < 30s")
                return False
        
        logger.debug("Can vote")
        return True
    
    def _is_day_allowed(self, now):
        """Check if the day is allowed"""
        allowed_days = self.pattern_config.get('allowed_days', [1,2,3,4,5,6])
        weekday = now.isoweekday()  # 1=Monday, 7=Sunday
        
        # Rest days
        rest_days = self.pattern_config.get('rest_days', [7])
        
        if weekday in rest_days:
            # On rest days, reduced probability
            if random.random() < 0.3:
                return True
            return False
            
        return weekday in allowed_days
    
    def _is_time_slot_allowed(self, now):
        """Check time slot with probability"""
        time_slots = self.pattern_config.get('time_slots', {})
        hour = now.hour
        
        # Find current time slot
        current_slot = None
        for name, slot in time_slots.items():
            if slot['start'] <= hour < slot['end']:
                current_slot = slot
                break
        
        if not current_slot:
            return False
        
        # Apply slot probability
        probability = current_slot.get('probability', 1.0)
        return random.random() < probability
    
    def register_vote(self):
        """Register a completed vote"""
        self.votes_today += 1
        self.last_vote = datetime.now()
        self.last_vote_day = datetime.now().date()
        
        percentage = (self.votes_today / self.config['max_votes_per_day']) * 100
        logger.info(f"Today: {self.votes_today}/{self.config['max_votes_per_day']} ({percentage:.1f}%)")
    
    def human_pause(self):
        """Pause with normal distribution and seasonal variation"""
        min_p = self.config['pause_min_between_votes']
        max_p = self.config['pause_max_between_votes']
        
        # Base normal distribution
        mean = (min_p + max_p) / 2
        stddev = (max_p - min_p) / 4
        pause = np.random.normal(mean, stddev)
        pause = max(min_p, min(max_p, pause))
        
        # Seasonal variation (if active)
        if self.pattern_config.get('seasonal_variation', False):
            month = datetime.now().month
            if 6 <= month <= 8:  # Summer months
                pause *= random.uniform(0.8, 1.2)
        
        logger.info(f"Pause {pause:.0f}s")
        time.sleep(pause)
    
    def time_until_next_vote(self):
        """Estimate time until next vote (useful for UI)"""
        if not self.last_vote:
            return 0
        
        now = datetime.now()
        minutes_passed = (now - self.last_vote).seconds / 60
        
        if minutes_passed < 0.5:
            return int((0.5 - minutes_passed) * 60)
        return 0