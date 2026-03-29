import random
import logging
import requests

logger = logging.getLogger(__name__)

class FingerprintManager:
    def __init__(self, config):
        self.config = config['fingerprint']
        self.geo_config = config.get('geolocation', {})
        self.browser_config = config.get('browser', {})
        self.webgl_config = config.get('webgl', {})
        
        # Country -> language mapping
        self.country_to_lang = {
            'IT': 'it-IT',
            'DE': 'de-DE',
            'FR': 'fr-FR',
            'ES': 'es-ES',
            'GB': 'en-GB',
            'US': 'en-US',
            'CA': 'en-CA',
            'AU': 'en-AU',
            'BR': 'pt-BR',
            'JP': 'ja-JP',
            'CN': 'zh-CN',
            'RU': 'ru-RU'
        }
        
        # Country -> timezone mapping
        self.country_to_tz = {
            'IT': 'Europe/Rome',
            'DE': 'Europe/Berlin',
            'FR': 'Europe/Paris',
            'ES': 'Europe/Madrid',
            'GB': 'Europe/London',
            'US': 'America/New_York',
            'CA': 'America/Toronto',
            'AU': 'Australia/Sydney',
            'BR': 'America/Sao_Paulo',
            'JP': 'Asia/Tokyo',
            'CN': 'Asia/Shanghai',
            'RU': 'Europe/Moscow'
        }
        
    def get_geo_info_from_ip(self, ip):
        """Get geographic information from an IP using external service"""
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode,region,city,timezone', timeout=3)
            if response.status_code == 200:
                data = response.json()
                return {
                    'country': data.get('countryCode', ''),
                    'timezone': data.get('timezone', ''),
                    'city': data.get('city', ''),
                    'region': data.get('region', '')
                }
        except:
            pass
        return None
        
    def generate(self, ip=None):
        # If we have an IP, try to get geolocation
        geo_info = None
        if ip:
            geo_info = self.get_geo_info_from_ip(ip)
        
        # If no IP info, use random geographic profile
        if not geo_info:
            geo_profile = self._select_geo_profile()
        else:
            geo_profile = {
                'country': geo_info.get('country', ''),
                'timezone': geo_info.get('timezone', ''),
                'language': self.country_to_lang.get(geo_info.get('country', ''), 'en-US')
            }
        
        browser_type, browser_version = self._select_browser()
        
        fingerprint = {
            'user_agent': self._generate_user_agent(browser_type, browser_version),
            'language': self._generate_language(geo_profile.get('language')) if geo_profile else random.choice(self.config['languages']),
            'resolution': random.choice(self.config['resolutions']),
            'timezone': geo_profile.get('timezone') if geo_profile else random.choice(self.config['timezones']),
            'canvas_noise': random.uniform(0.0001, 0.001) if self.config.get('canvas_noise', False) else 0,
            'webgl_noise': random.uniform(0.0001, 0.001) if self.config.get('webgl_noise', False) else 0,
            'audio_noise': random.uniform(0.0001, 0.001) if self.config.get('audio_noise', False) else 0,
            'platform': self._generate_platform(browser_type),
            'cores': random.choice(self.config.get('cores', [4, 8])),
            'ram': random.choice(self.config.get('ram', [8, 16])),
            'font': random.choice(self.config.get('fonts', ['Arial,Helvetica,sans-serif'])),
            'do_not_track': random.choice(self.config.get('do_not_track', [False, True, None])),
            'hardware_concurrency': random.choice(self.config.get('hardware_concurrency', [4, 8])),
            'device_memory': random.choice(self.config.get('device_memory', [8, 16])),
            'max_touch_points': random.choice(self.config.get('max_touch_points', [0, 5, 10])),
            'webgl_vendor': random.choice(self.webgl_config.get('vendors', ['Google Inc. (Intel)'])),
            'webgl_renderer': random.choice(self.webgl_config.get('renderers', ['Intel Iris OpenGL Engine']))
        }
        
        if geo_profile:
            fingerprint['country'] = geo_profile.get('country', 'Unknown')
        
        return fingerprint
    
    def _select_geo_profile(self):
        if not self.geo_config.get('active', False):
            return None
            
        profiles = self.geo_config.get('profiles', [])
        if not profiles:
            return None
            
        probabilities = [p.get('probability', 0) for p in profiles]
        if sum(probabilities) != 1:
            probabilities = [1/len(profiles)] * len(profiles)
            
        return random.choices(profiles, weights=probabilities)[0]
    
    def _select_browser(self):
        browser_types = self.browser_config.get('types', ['firefox'])
        versions = self.browser_config.get('versions', {})
        
        browser_type = random.choice(browser_types)
        browser_versions = versions.get(browser_type, ['115.0'])
        browser_version = random.choice(browser_versions)
        
        return browser_type, browser_version
    
    def _generate_user_agent(self, browser_type, version):
        if browser_type == 'firefox':
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}"
        elif browser_type == 'chrome':
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36"
        elif browser_type == 'edge':
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version}.0.0.0 Safari/537.36 Edg/{version}.0.0.0"
        elif browser_type == 'safari':
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15"
        else:
            return random.choice(self.config['user_agents'])
    
    def _generate_language(self, language_base=None):
        if language_base:
            if language_base.startswith('it'):
                return f"{language_base},it;q=0.9,en;q=0.8"
            elif language_base.startswith('de'):
                return f"{language_base},de;q=0.9,en;q=0.8"
            elif language_base.startswith('fr'):
                return f"{language_base},fr;q=0.9,en;q=0.8"
            elif language_base.startswith('es'):
                return f"{language_base},es;q=0.9,en;q=0.8"
            elif language_base.startswith('pt'):
                return f"{language_base},pt;q=0.9,en;q=0.8"
            else:
                return f"{language_base},en;q=0.9"
        else:
            return random.choice(self.config['languages'])
    
    def _generate_platform(self, browser_type):
        platforms = self.config.get('platforms', ['Win32', 'Win64'])
        
        if browser_type == 'safari':
            return 'MacIntel'
        elif browser_type in ['chrome', 'firefox', 'edge']:
            return random.choice(['Win64', 'MacIntel', 'Linux x86_64'])
        else:
            return random.choice(platforms)
    
    def apply(self, options, fingerprint):
        options.set_preference('general.useragent.override', fingerprint['user_agent'])
        options.set_preference('intl.accept_languages', fingerprint['language'])
        options.set_preference('privacy.resistFingerprinting', True)
        options.set_preference('privacy.trackingprotection.fingerprinting.enabled', True)
        options.set_preference('browser.cache.disk.enable', False)
        options.set_preference('browser.cache.memory.enable', False)
        options.set_preference('dom.max_script_run_time', 20)
        options.set_preference('dom.max_chrome_script_run_time', 20)
        
        if fingerprint.get('do_not_track') is True:
            options.set_preference('privacy.donottrackheader.enabled', True)
        elif fingerprint.get('do_not_track') is False:
            options.set_preference('privacy.donottrackheader.enabled', False)
        
        options.set_preference('webgl.disabled', False)
        options.set_preference('webgl.enable-webgl2', True)
        
        country = fingerprint.get('country', 'Unknown')
        logger.info(f"Browser: {country} | UA: {fingerprint['user_agent'][:30]}...")
        return options