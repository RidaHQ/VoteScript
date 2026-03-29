import time
import logging
import requests
from stem import Signal
from stem.control import Controller
import socket
import subprocess
import os

logging.getLogger('stem').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

class TorManager:
    def __init__(self, proxy, control_port):
        self.proxy = proxy
        self.control_port = control_port
        self.current_ip = None
        self.previous_ip = None
        self.max_retry = 3
        self.retry_delay = 2
        self.tor_process = None
        
    def test_control_port(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', self.control_port))
            sock.close()
            return result == 0
        except:
            return False
    
    def wait_for_control_port(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            if self.test_control_port():
                return True
            logger.debug(f"Waiting for ControlPort... ({int(time.time() - start)}s)")
            time.sleep(1)
        return False
    
    def get_ip(self, attempts=3):
        for attempt in range(attempts):
            try:
                proxies = {
                    'http': f'socks5h://{self.proxy}',
                    'https': f'socks5h://{self.proxy}'
                }
                response = requests.get('https://api.ipify.org', proxies=proxies, timeout=5)
                if response.status_code == 200:
                    return response.text
                return None
            except Exception as e:
                logger.debug(f"Attempt {attempt+1}/{attempts} get_ip failed: {e}")
                if attempt < attempts - 1:
                    time.sleep(self.retry_delay)
        return None
    
    def get_ip_info(self, ip):
        """Get geographic information for an IP"""
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode,region,city,timezone', timeout=3)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def change_ip(self, max_attempts=5, callback=None):
        if not self.wait_for_control_port(timeout=10):
            logger.warning(f"ControlPort {self.control_port} not available")
            return False
        
        ip_before = self.get_ip(attempts=2)
        if ip_before:
            logger.info(f"IP BEFORE: {ip_before}")
        else:
            logger.warning("Unable to get current IP")
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"IP change attempt {attempt+1}/{max_attempts}")
                
                controller = Controller.from_port(port=self.control_port)
                controller.connect()
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                controller.close()
                
                logger.info(f"NEWNYM signal sent (attempt {attempt+1})")
                
                for wait_cycle in range(6):
                    time.sleep(2)
                    ip_after = self.get_ip(attempts=1)
                    if ip_after:
                        if ip_after != ip_before:
                            logger.info(f"IP CHANGED: {ip_before} -> {ip_after}")
                            self.current_ip = ip_after
                            
                            # Get geographic info
                            geo_info = self.get_ip_info(ip_after)
                            if geo_info:
                                logger.info(f"   {geo_info.get('country', 'Unknown')} - {geo_info.get('city', 'Unknown')}")
                            
                            if callback:
                                callback(ip_after)
                            return True
                    else:
                        logger.debug(f"IP not available after {wait_cycle*2+2}s")
                
                logger.warning(f"IP not changed in attempt {attempt+1}")
                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {e}")
            
            if attempt < max_attempts - 1:
                pause = self.retry_delay * (2 ** attempt)
                logger.info(f"Waiting {pause}s before next attempt")
                time.sleep(pause)
        
        logger.error("IP change failed after all attempts")
        return False
    
    def verify_connection(self):
        try:
            ip = self.get_ip()
            if ip:
                logger.info(f"Tor active - IP: {ip}")
                
                for attempt in range(10):
                    if self.test_control_port():
                        logger.info(f"ControlPort {self.control_port} active")
                        return True
                    logger.debug(f"Waiting for ControlPort... attempt {attempt+1}/10")
                    time.sleep(1)
                
                logger.warning(f"ControlPort {self.control_port} not responding after 10s")
                return True
            return False
        except Exception as e:
            logger.error(f"Tor unreachable: {e}")
            return False
    
    def stop_tor(self):
        """Completely stop Tor"""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "tor.exe"], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("Tor stopped")
            self.current_ip = None
            return True
        except Exception as e:
            logger.error(f"Error stopping Tor: {e}")
            return False