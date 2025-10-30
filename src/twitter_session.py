import logging
from typing import Dict, Optional
import time


class TwitterSession:
    
    def __init__(self, username: str, email: str, password: str, twitter_settings: Optional[Dict] = None):
        self.username = username
        self.email = email
        self.password = password
        self.twitter_settings = twitter_settings or {}
        self.logger = logging.getLogger(__name__)
        
        self.is_logged_in = False
        self.session_start_time = None
        
        self.logger.info(f"Twitter session initialized for account: {username}")
    
    def get_credentials(self) -> Dict[str, str]:
        return {
            'username': self.username,
            'email': self.email,
            'password': self.password
        }
    
    def mark_logged_in(self) -> None:
        self.is_logged_in = True
        self.session_start_time = time.time()
        self.logger.info(f"Session marked as logged in for @{self.username}")
    
    def mark_logged_out(self) -> None:
        self.is_logged_in = False
        self.session_start_time = None
        self.logger.info(f"Session marked as logged out for @{self.username}")
    
    def get_session_info(self) -> Dict:
        session_duration = None
        if self.is_logged_in and self.session_start_time:
            session_duration = time.time() - self.session_start_time
        
        return {
            'username': self.username,
            'is_logged_in': self.is_logged_in,
            'session_duration': session_duration
        }

