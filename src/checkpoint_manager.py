import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


class CheckpointManager:
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger(__name__)
    
    def get_checkpoint_file(self, username: str) -> Path:
        user_dir = self.base_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "checkpoint.json"
    
    def get_tweets_file(self, username: str) -> Path:
        user_dir = self.base_dir / username
        return user_dir / f"tweets_{username}.json"
    
    def load_checkpoint(self, username: str) -> Optional[Dict]:
        checkpoint_file = self.get_checkpoint_file(username)
        
        if not checkpoint_file.exists():
            self.logger.info(f"No checkpoint found for @{username}")
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            self.logger.info(f"Checkpoint loaded for @{username}:")
            self.logger.info(f"   - Last scraped: {checkpoint.get('last_tweet_date', 'Unknown')}")
            self.logger.info(f"   - Total tweets: {checkpoint.get('total_tweets', 0)}")
            self.logger.info(f"   - Sessions: {checkpoint.get('session_count', 1)}")
            
            return checkpoint
            
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def save_checkpoint(self, username: str, checkpoint_data: Dict):
        checkpoint_file = self.get_checkpoint_file(username)
        
        try:
            checkpoint_data['username'] = username
            checkpoint_data['last_updated'] = datetime.now().isoformat()
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
            
            self.logger.info(f"Checkpoint saved for @{username}")
            self.logger.info(f"   - Total tweets: {checkpoint_data.get('total_tweets', 0)}")
            self.logger.info(f"   - Oldest tweet: {checkpoint_data.get('oldest_tweet_date', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
    
    def load_existing_tweets(self, username: str) -> List[Dict]:
        tweets_file = self.get_tweets_file(username)
        
        if not tweets_file.exists():
            self.logger.info(f"No existing tweets file found for @{username}")
            return []
        
        try:
            with open(tweets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            tweets = data.get('tweets', [])
            self.logger.info(f"Loaded {len(tweets)} existing tweets for @{username}")
            return tweets
            
        except Exception as e:
            self.logger.error(f"Failed to load existing tweets: {e}")
            return []
    
    def save_all_tweets(self, username: str, all_tweets: List[Dict], user_data: Optional[Dict] = None, 
                       checkpoint_data: Optional[Dict] = None):
        tweets_file = self.get_tweets_file(username)
        
        try:
            unique_tweets = {}
            for tweet in all_tweets:
                tweet_id = tweet.get('id')
                if tweet_id and tweet_id not in unique_tweets:
                    unique_tweets[tweet_id] = tweet
            
            sorted_tweets = sorted(
                unique_tweets.values(),
                key=lambda x: int(x.get('id', '0')) if x.get('id', '').isdigit() else 0,
                reverse=True
            )
            
            output_data = {
                'username': username,
                'user_data': user_data,
                'tweet_count': len(sorted_tweets),
                'unique_tweet_count': len(sorted_tweets),
                'last_updated': datetime.now().isoformat(),
                'session_count': checkpoint_data.get('session_count', 1) if checkpoint_data else 1,
                'oldest_tweet_date': checkpoint_data.get('oldest_tweet_date') if checkpoint_data else None,
                'tweets': sorted_tweets
            }
            
            with open(tweets_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Saved {len(sorted_tweets)} total tweets to {tweets_file.name}")
            
            return len(sorted_tweets)
            
        except Exception as e:
            self.logger.error(f"Failed to save tweets: {e}")
            return 0
    
    def merge_tweets(self, existing_tweets: List[Dict], new_tweets: List[Dict]) -> List[Dict]:
        
        all_tweets = {}
        
        for tweet in existing_tweets:
            tweet_id = tweet.get('id')
            if tweet_id:
                all_tweets[tweet_id] = tweet
        
        new_count = 0
        for tweet in new_tweets:
            tweet_id = tweet.get('id')
            if tweet_id:
                if tweet_id not in all_tweets:
                    new_count += 1
                all_tweets[tweet_id] = tweet
        
        self.logger.info(f"Merged: {len(existing_tweets)} existing + {new_count} new = {len(all_tweets)} total")
        
        return list(all_tweets.values())
    
    def has_checkpoint(self, username: str) -> bool:
        
        return self.get_checkpoint_file(username).exists()
    
    def delete_checkpoint(self, username: str):
        
        checkpoint_file = self.get_checkpoint_file(username)
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            self.logger.info(f"Deleted checkpoint for @{username}")

