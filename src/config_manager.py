import configparser
from typing import Dict, Any
from pathlib import Path

from .exceptions import InvalidConfigError, MissingConfigError


class ConfigManager:
    
    def __init__(self, config_path: str = "config.ini"):
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self) -> None:
        if not self.config_path.exists():
            raise MissingConfigError(f"Configuration file not found: {self.config_path}")
        
        try:
            self.config.read(self.config_path)
            self._validate_config()
        except InvalidConfigError:
            raise
        except MissingConfigError:
            raise
        except Exception as e:
            raise InvalidConfigError(f"Failed to parse configuration file: {e}") from e
    
    def get_twitter_credentials(self) -> Dict[str, str]:
        """Get Twitter account credentials from config."""
        if not self.config.has_section('TWITTER'):
            return {'username': '', 'email': '', 'password': ''}
        
        return {
            'username': self.config.get('TWITTER', 'username', fallback=''),
            'email': self.config.get('TWITTER', 'email', fallback=''),
            'password': self.config.get('TWITTER', 'password', fallback='')
        }
    
    def get_ai_settings(self) -> Dict[str, Any]:
        return {
            'openai_api_key': self.config.get('AI', 'openai_api_key', fallback=''),
            'model': self.config.get('AI', 'model', fallback='gpt-4'),
            'max_tokens': self.config.getint('AI', 'max_tokens', fallback=1000),
            'temperature': self.config.getfloat('AI', 'temperature', fallback=0.7)
        }
    
    def get_scraping_settings(self) -> Dict[str, Any]:
        return {
            'default_tweet_count': self.config.getint('SCRAPING', 'default_tweet_count', fallback=50),
            'max_tweet_count': self.config.getint('SCRAPING', 'max_tweet_count', fallback=1000),
            'save_to_file': self.config.getboolean('SCRAPING', 'save_to_file', fallback=True),
            'output_format': self.config.get('SCRAPING', 'output_format', fallback='json'),
            'output_directory': self.config.get('SCRAPING', 'output_directory', fallback='./data'),
            'scroll_delay_min': self.config.getfloat('SCRAPING', 'scroll_delay_min', fallback=3.0),
            'scroll_delay_max': self.config.getfloat('SCRAPING', 'scroll_delay_max', fallback=6.0),
            'max_scroll_attempts': self.config.getint('SCRAPING', 'max_scroll_attempts', fallback=5000),
            'max_attempts_without_new': self.config.getint('SCRAPING', 'max_attempts_without_new', fallback=50),
            'max_tweets_per_session': self.config.getint('SCRAPING', 'max_tweets_per_session', fallback=800),
            'overlap_detection_threshold': self.config.getint('SCRAPING', 'overlap_detection_threshold', fallback=5)
        }
    
    def get_timeout_settings(self) -> Dict[str, Any]:
        return {
            'page_load_timeout': self.config.getint('TIMEOUTS', 'page_load_timeout', fallback=60000),
            'element_wait_timeout': self.config.getint('TIMEOUTS', 'element_wait_timeout', fallback=30000),
            'button_click_timeout': self.config.getint('TIMEOUTS', 'button_click_timeout', fallback=10000),
            'cookie_verification_timeout': self.config.getint('TIMEOUTS', 'cookie_verification_timeout', fallback=15000),
            'login_complete_timeout': self.config.getint('TIMEOUTS', 'login_complete_timeout', fallback=20000),
            'short_wait_timeout': self.config.getint('TIMEOUTS', 'short_wait_timeout', fallback=5000),
            'post_login_page_delay': self.config.getfloat('TIMEOUTS', 'post_login_page_delay', fallback=5.0),
            'post_input_delay': self.config.getfloat('TIMEOUTS', 'post_input_delay', fallback=2.0),
            'post_navigation_delay': self.config.getfloat('TIMEOUTS', 'post_navigation_delay', fallback=3.0),
            'post_click_delay': self.config.getfloat('TIMEOUTS', 'post_click_delay', fallback=3.0),
            'verification_check_delay': self.config.getfloat('TIMEOUTS', 'verification_check_delay', fallback=2.0),
            'login_wait_delay': self.config.getfloat('TIMEOUTS', 'login_wait_delay', fallback=8.0),
            'page_refresh_short_delay': self.config.getfloat('TIMEOUTS', 'page_refresh_short_delay', fallback=2.0),
            'page_refresh_long_delay': self.config.getfloat('TIMEOUTS', 'page_refresh_long_delay', fallback=3.0)
        }
    
    def get_search_settings(self) -> Dict[str, Any]:
        return {
            'enable_historical_search': self.config.getboolean('SEARCH', 'enable_historical_search', fallback=True),
            'chunk_type': self.config.get('SEARCH', 'chunk_type', fallback='monthly'),
            'max_tweets_per_date_range': self.config.getint('SEARCH', 'max_tweets_per_date_range', fallback=500),
            'search_delay_between_ranges': self.config.getfloat('SEARCH', 'search_delay_between_ranges', fallback=5.0)
        }
    
    def get_logging_settings(self) -> Dict[str, Any]:
        return {
            'level': self.config.get('LOGGING', 'level', fallback='INFO'),
            'log_to_file': self.config.getboolean('LOGGING', 'log_to_file', fallback=True),
            'log_file': self.config.get('LOGGING', 'log_file', fallback='./logs/scraper.log'),
            'max_log_size': self.config.getint('LOGGING', 'max_log_size', fallback=10485760),
            'backup_count': self.config.getint('LOGGING', 'backup_count', fallback=5)
        }
    
    def get_filter_settings(self) -> Dict[str, Any]:
        return {
            'min_followers': self.config.getint('FILTERS', 'min_followers', fallback=0),
            'verified_only': self.config.getboolean('FILTERS', 'verified_only', fallback=False),
            'exclude_retweets': self.config.getboolean('FILTERS', 'exclude_retweets', fallback=False),
            'exclude_replies': self.config.getboolean('FILTERS', 'exclude_replies', fallback=False),
            'language': self.config.get('FILTERS', 'language', fallback='en')
        }
    
    def get_proxy_settings(self) -> Dict[str, Any]:
        proxy_settings = {
            'enable_proxy_rotation': self.config.getboolean('PROXY', 'enable_proxy_rotation', fallback=False),
            'validate_proxies_on_startup': self.config.getboolean('PROXY', 'validate_proxies_on_startup', fallback=True),
            'rotation_url': self.config.get('PROXY', 'proxy_rotation_url', fallback=''),
            'proxies': []
        }
        
        proxy_list_str = self.config.get('PROXY', 'proxy_list', fallback='')
        if proxy_list_str.strip():
            proxy_list = [proxy.strip() for proxy in proxy_list_str.split(',') if proxy.strip()]
            proxy_settings['proxies'] = proxy_list
        
        return proxy_settings
    
    def get_setting(self, section: str, key: str, fallback: Any = None) -> Any:
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def update_setting(self, section: str, key: str, value: str) -> None:
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, key, str(value))
    
    def save_config(self) -> None:
        with open(self.config_path, 'w') as config_file:
            self.config.write(config_file)
    
    def _validate_config(self) -> None:
        errors = []
        
        if not self.config.has_section('TWITTER'):
            errors.append("Missing required section: [TWITTER]")
        
        if self.config.has_section('TWITTER'):
            required_twitter = ['username', 'email', 'password']
            for field in required_twitter:
                value = self.config.get('TWITTER', field, fallback='')
                if not value or value.strip() == '':
                    errors.append(f"Missing required field: [TWITTER] {field}")
        
        if not self.config.has_section('SCRAPING'):
            errors.append("Missing required section: [SCRAPING]")
        
        if self.config.has_section('SCRAPING'):
            try:
                max_tweets = self.config.getint('SCRAPING', 'max_tweets_per_session')
                if max_tweets < 1:
                    errors.append(f"[SCRAPING] max_tweets_per_session must be >= 1, got {max_tweets}")
            except ValueError as e:
                errors.append(f"[SCRAPING] max_tweets_per_session must be a valid integer: {e}")
            
            try:
                scroll_min = self.config.getfloat('SCRAPING', 'scroll_delay_min', fallback=1.0)
                scroll_max = self.config.getfloat('SCRAPING', 'scroll_delay_max', fallback=3.0)
                
                if scroll_min < 0:
                    errors.append(f"[SCRAPING] scroll_delay_min must be >= 0, got {scroll_min}")
                if scroll_max < scroll_min:
                    errors.append(f"[SCRAPING] scroll_delay_max ({scroll_max}) must be >= scroll_delay_min ({scroll_min})")
            except ValueError as e:
                errors.append(f"[SCRAPING] Invalid scroll delay values: {e}")
            
            try:
                max_scrolls = self.config.getint('SCRAPING', 'max_scroll_attempts', fallback=100)
                if max_scrolls < 1:
                    errors.append(f"[SCRAPING] max_scroll_attempts must be >= 1, got {max_scrolls}")
            except ValueError as e:
                errors.append(f"[SCRAPING] max_scroll_attempts must be a valid integer: {e}")
            
            output_dir = self.config.get('SCRAPING', 'output_directory', fallback='')
            if not output_dir:
                errors.append(f"Missing required field: [SCRAPING] output_directory")
        
        if self.config.has_section('AI'):
            provider = self.config.get('AI', 'provider', fallback='').lower()
            if provider and provider not in ['openai', 'anthropic', 'none']:
                errors.append(f"[AI] Invalid provider '{provider}'. Must be: openai, anthropic, or none")
            
            if provider in ['openai', 'anthropic']:
                api_key = self.config.get('AI', 'api_key', fallback='')
                if not api_key or api_key.strip() == '':
                    errors.append(f"[AI] api_key is required when provider is '{provider}'")
            
            try:
                max_tokens = self.config.getint('AI', 'max_tokens', fallback=1000)
                if max_tokens < 1:
                    errors.append(f"[AI] max_tokens must be >= 1, got {max_tokens}")
            except ValueError as e:
                errors.append(f"[AI] max_tokens must be a valid integer: {e}")
        
        if self.config.has_section('TIMEOUTS'):
            for field in self.config.options('TIMEOUTS'):
                try:
                    value = self.config.getfloat('TIMEOUTS', field)
                    if value < 0:
                        errors.append(f"[TIMEOUTS] {field} must be >= 0, got {value}")
                except ValueError as e:
                    errors.append(f"[TIMEOUTS] {field} must be a valid number: {e}")
        
        if self.config.has_section('SEARCH'):
            try:
                max_per_range = self.config.getint('SEARCH', 'max_tweets_per_date_range', fallback=500)
                if max_per_range < 1:
                    errors.append(f"[SEARCH] max_tweets_per_date_range must be >= 1, got {max_per_range}")
            except ValueError as e:
                errors.append(f"[SEARCH] max_tweets_per_date_range must be a valid integer: {e}")
            
            try:
                delay = self.config.getint('SEARCH', 'search_delay_between_ranges', fallback=30)
                if delay < 0:
                    errors.append(f"[SEARCH] search_delay_between_ranges must be >= 0, got {delay}")
            except ValueError as e:
                errors.append(f"[SEARCH] search_delay_between_ranges must be a valid integer: {e}")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise InvalidConfigError(error_msg)