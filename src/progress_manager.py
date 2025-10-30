import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ScrapingProgress:
    target_type: str 
    target_value: str 
    total_requested: int
    total_scraped: int
    last_tweet_id: Optional[str]
    last_cursor: Optional[str]
    start_time: float
    last_update: float
    accounts_used: List[str]
    completed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapingProgress':
        return cls(**data)


class ProgressManager:
    
    def __init__(self, progress_dir: str = "./data/progress"):
        self.progress_dir = Path(progress_dir)
        self.progress_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        self.current_progress: Optional[ScrapingProgress] = None
        
    def _get_progress_file(self, target_type: str, target_value: str) -> Path:
        clean_target = target_value.replace('@', '').replace(' ', '_').replace('/', '_')
        return self.progress_dir / f"{target_type}_{clean_target}_progress.json"
    
    def load_progress(self, target_type: str, target_value: str) -> Optional[ScrapingProgress]:
        progress_file = self._get_progress_file(target_type, target_value)
        
        if not progress_file.exists():
            return None
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            progress = ScrapingProgress.from_dict(data)
            self.logger.info(f"Loaded progress: {progress.total_scraped}/{progress.total_requested} tweets")
            return progress
            
        except Exception as e:
            self.logger.error(f"Failed to load progress: {str(e)}")
            return None
    
    def save_progress(self, progress: ScrapingProgress) -> bool:
        try:
            progress_file = self._get_progress_file(progress.target_type, progress.target_value)
            progress.last_update = time.time()
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress.to_dict(), f, indent=2)
            
            self.logger.debug(f"Progress saved: {progress.total_scraped}/{progress.total_requested}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save progress: {str(e)}")
            return False
    
    def start_scraping(self, target_type: str, target_value: str, 
                      total_requested: int, resume: bool = False) -> ScrapingProgress:
        
        if resume:
            existing_progress = self.load_progress(target_type, target_value)
            if existing_progress and not existing_progress.completed:
                if existing_progress.total_requested != total_requested:
                    existing_progress.total_requested = total_requested
                    existing_progress.completed = False
                
                self.current_progress = existing_progress
                self.logger.info(f"Resuming scraping from {existing_progress.total_scraped} tweets")
                return existing_progress
        
        self.current_progress = ScrapingProgress(
            target_type=target_type,
            target_value=target_value,
            total_requested=total_requested,
            total_scraped=0,
            last_tweet_id=None,
            last_cursor=None,
            start_time=time.time(),
            last_update=time.time(),
            accounts_used=[],
            completed=False
        )
        
        self.save_progress(self.current_progress)
        self.logger.info(f"Started new scraping session: 0/{total_requested} tweets")
        return self.current_progress
    
    def update_progress(self, tweets_scraped: int, last_tweet_id: Optional[str] = None,
                       last_cursor: Optional[str] = None, account_used: Optional[str] = None) -> bool:
        if not self.current_progress:
            return False
        
        self.current_progress.total_scraped += tweets_scraped
        
        if last_tweet_id:
            self.current_progress.last_tweet_id = last_tweet_id
        
        if last_cursor:
            self.current_progress.last_cursor = last_cursor
        
        if account_used and account_used not in self.current_progress.accounts_used:
            self.current_progress.accounts_used.append(account_used)
        
        if self.current_progress.total_scraped >= self.current_progress.total_requested:
            self.current_progress.completed = True
            self.logger.info(f"Scraping completed: {self.current_progress.total_scraped} tweets")
        
        return self.save_progress(self.current_progress)
    
    def get_resume_info(self, target_type: str, target_value: str) -> Optional[Dict[str, Any]]:
        progress = self.load_progress(target_type, target_value)
        if not progress or progress.completed:
            return None
        
        remaining = progress.total_requested - progress.total_scraped
        elapsed = time.time() - progress.start_time
        
        return {
            "total_requested": progress.total_requested,
            "total_scraped": progress.total_scraped,
            "remaining": remaining,
            "completion_percentage": (progress.total_scraped / progress.total_requested) * 100,
            "elapsed_time": elapsed,
            "last_tweet_id": progress.last_tweet_id,
            "last_cursor": progress.last_cursor,
            "accounts_used": progress.accounts_used,
            "can_resume": True
        }
    
    def complete_scraping(self) -> bool:

        if not self.current_progress:
            return False
        
        self.current_progress.completed = True
        return self.save_progress(self.current_progress)
    
    def clear_progress(self, target_type: str, target_value: str) -> bool:
        try:
            progress_file = self._get_progress_file(target_type, target_value)
            if progress_file.exists():
                progress_file.unlink()
                self.logger.info(f"Cleared progress for {target_type}: {target_value}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear progress: {str(e)}")
            return False
    
    def list_incomplete_sessions(self) -> List[Dict[str, Any]]:
        incomplete = []
        
        for progress_file in self.progress_dir.glob("*_progress.json"):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                progress = ScrapingProgress.from_dict(data)
                if not progress.completed:
                    incomplete.append({
                        "target_type": progress.target_type,
                        "target_value": progress.target_value,
                        "progress": f"{progress.total_scraped}/{progress.total_requested}",
                        "completion_percentage": (progress.total_scraped / progress.total_requested) * 100,
                        "last_update": progress.last_update,
                        "file": str(progress_file)
                    })
            except Exception as e:
                self.logger.error(f"Error reading progress file {progress_file}: {str(e)}")
        
        return incomplete
    
    def get_current_progress(self) -> Optional[ScrapingProgress]:
        return self.current_progress