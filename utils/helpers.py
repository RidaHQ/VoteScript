"""
Generic utility functions
"""
import os
import json
import time
import random
import hashlib
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

def load_json(filepath: str, default: Any = None) -> Any:
    """Safely load a JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default

def save_json(filepath: str, data: Any) -> bool:
    """Save data to JSON file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

def generate_hash(string: str) -> str:
    """Generate MD5 hash of a string"""
    return hashlib.md5(string.encode()).hexdigest()

def timestamp() -> int:
    """Return current timestamp"""
    return int(time.time())

def today_date() -> str:
    """Return today's date in YYYY-MM-DD format"""
    return datetime.now().strftime('%Y-%m-%d')

def current_time() -> str:
    """Return current time in HH:MM:SS format"""
    return datetime.now().strftime('%H:%M:%S')

def human_pause(min_sec: float, max_sec: float):
    """Pause with normal distribution"""
    mean = (min_sec + max_sec) / 2
    stddev = (max_sec - min_sec) / 4
    pause = random.normalvariate(mean, stddev)
    pause = max(min_sec, min(max_sec, pause))
    time.sleep(pause)

def kill_process(process_name: str) -> bool:
    """Kill a process by name"""
    try:
        if platform.system() == 'Windows':
            subprocess.run(f'taskkill /F /IM {process_name}', shell=True)
        else:
            subprocess.run(f'pkill -f {process_name}', shell=True)
        return True
    except:
        return False

def port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    """Check if a port is in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((host, port))
            return True
        except:
            return False

def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Wait for a port to become available"""
    start = time.time()
    while time.time() - start < timeout:
        if port_in_use(port):
            return True
        time.sleep(1)
    return False

class Timer:
    """Timer for performance measurement"""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        if self.name:
            print(f"{self.name}: {elapsed:.3f}s")
    
    @property
    def elapsed(self):
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

class RateLimiter:
    """Frequency limiter"""
    
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def allows(self) -> bool:
        now = time.time()
        # Remove old calls
        self.calls = [t for t in self.calls if t > now - self.period]
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False
    
    def wait_required(self) -> float:
        if not self.calls:
            return 0
        now = time.time()
        oldest = min(self.calls)
        return max(0, (oldest + self.period) - now)

class Statistics:
    """Collects execution statistics"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.start = time.time()
        self.counts = {}
        self.times = {}
    
    def increment(self, key: str):
        self.counts[key] = self.counts.get(key, 0) + 1
    
    def register_time(self, key: str, duration: float):
        if key not in self.times:
            self.times[key] = []
        self.times[key].append(duration)
    
    def report(self) -> Dict:
        elapsed = time.time() - self.start
        return {
            'duration': elapsed,
            'counts': self.counts,
            'averages': {
                k: sum(v)/len(v) if v else 0
                for k, v in self.times.items()
            }
        }

def truncate_text(text: str, max_len: int = 50) -> str:
    """Truncate text for logging"""
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for c in invalid_chars:
        filename = filename.replace(c, '_')
    return filename

class PersistentMemory:
    """Simple file-based memory"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = self.load()
    
    def load(self) -> Dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get(self, key: str, default=None):
        return self.data.get(key, default)
    
    def set(self, key: str, value):
        self.data[key] = value
        self.save()