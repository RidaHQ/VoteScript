#!/usr/bin/env python3
import sys
import json
import logging
import random
import time
import os
from datetime import datetime
from core.voter import Voter
from strategies.temporal import TemporalManager
from core.tor_manager import TorManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('main')

def load_config(path: str = None):
    if path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "config", "config.json")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.error(f"Config load error: {e}")
        sys.exit(1)

def run_bot(config, stop_event=None, stats_callback=None, vote_callback=None, 
            block_callback=None, ip_callback=None, title_callback=None, pause_event=None,
            history_active=True, link_toggle_states=None):
    
    total_ip_changes = config['total_votes']  # esempio: 5000
    total_votes = len(config['target_urls']) * total_ip_changes  # esempio: 5000 * 5 = 25000
    
    logger.info(f"Target: {total_ip_changes} IP changes, {total_votes} total votes")
    
    tester = TorManager(config['tor_proxy'], config['tor_control_port'])
    connected = False
    for attempt in range(10):
        if stop_event and stop_event.is_set():
            logger.info("Stop requested")
            return
        if tester.verify_connection():
            connected = True
            break
        logger.info(f"Waiting for Tor... attempt {attempt+1}/10")
        time.sleep(3)
    if not connected:
        logger.error("Tor not working after 10 attempts")
        return
    
    votes_done = 0
    ip_changes = 0
    
    if stats_callback:
        stats_callback(ip_changes, votes_done, total_votes, total_ip_changes, tester.get_ip())
    
    while ip_changes < total_ip_changes:
        if stop_event and stop_event.is_set():
            logger.info("Stop requested, interrupting")
            break
        while pause_event and pause_event.is_set():
            logger.info("Bot paused...")
            time.sleep(1)
            if stop_event and stop_event.is_set():
                logger.info("Stop requested during pause")
                return
        
        ip_changes += 1
        logger.info(f"IP CHANGE #{ip_changes}/{total_ip_changes}")
        ip_before = tester.get_ip()
        
        if stats_callback:
            stats_callback(ip_changes, votes_done, total_votes, total_ip_changes, ip_before)
        
        voter = Voter(config)
        votes_this_ip = voter.vote_all_links(
            stop_event, vote_callback, block_callback, ip_callback, title_callback, 
            pause_event, history_active, link_toggle_states
        )
        votes_done += votes_this_ip
        ip_after = tester.get_ip()
        
        logger.info(f"IP after: {ip_after}")
        logger.info(f"Progress: {ip_changes}/{total_ip_changes} changes - {votes_done}/{total_votes} votes")
        
        if stats_callback and ip_after:
            stats_callback(ip_changes, votes_done, total_votes, total_ip_changes, ip_after)
        
        if ip_changes < total_ip_changes and (not stop_event or not stop_event.is_set()):
            pause = random.uniform(5, 10)
            logger.info(f"Pause {pause:.0f}s")
            for i in range(int(pause * 2)):
                if stop_event and stop_event.is_set():
                    logger.info("Stop requested during pause")
                    break
                if pause_event and pause_event.is_set():
                    logger.info("Pause requested")
                    while pause_event.is_set():
                        time.sleep(0.5)
                time.sleep(0.5)
    
    logger.info(f"\nFINAL REPORT")
    logger.info(f"Completed: {ip_changes}/{total_ip_changes} changes")
    logger.info(f"Total votes: {votes_done}/{total_votes}")
    
    if stats_callback:
        stats_callback(ip_changes, votes_done, total_votes, total_ip_changes, ip_after if 'ip_after' in locals() else "N/A")

def run_bot_with_callback(config, stop_event, stats_callback, vote_callback=None, 
                          block_callback=None, ip_callback=None, title_callback=None, 
                          pause_event=None, history_active=True, link_toggle_states=None):
    return run_bot(config, stop_event, stats_callback, vote_callback, block_callback, 
                   ip_callback, title_callback, pause_event, history_active, link_toggle_states)

def main(config_path: str = None):
    config = load_config(config_path)
    run_bot(config)

if __name__ == "__main__":
    main()
