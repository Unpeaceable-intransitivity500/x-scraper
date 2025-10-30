import asyncio
import logging
import logging.handlers
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiofiles
import pandas as pd
from .config_manager import ConfigManager
from .twitter_session import TwitterSession
from .playwright_scraper import PlaywrightScraper
from .ai_analyzer import AIAnalyzer, AnalysisType
from .progress_manager import ProgressManager
from .checkpoint_manager import CheckpointManager


class XScraper:
    
    def __init__(self, config_path: str = "config.ini"):
        self.config_manager = ConfigManager(config_path)
        self.logger = self._setup_logging()
        
        self.twitter_session: Optional[TwitterSession] = None
        self.playwright_scraper: Optional[PlaywrightScraper] = None
        self.ai_analyzer: Optional[AIAnalyzer] = None
        self.progress_manager: Optional[ProgressManager] = None
        self.checkpoint_manager: CheckpointManager = CheckpointManager()
        
        self.is_running = False
        self.scraped_tweets = []
        self.session_stats = {
            'start_time': None,
            'end_time': None,
            'tweets_scraped': 0,
            'analyses_performed': 0,
            'errors_encountered': 0
        }
        
        self._initialize_components()
    
    def _setup_logging(self) -> logging.Logger:
        logging_settings = self.config_manager.get_logging_settings()
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, logging_settings['level']))
        root_logger.handlers.clear()
        
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        if logging_settings['log_to_file']:
            log_file = Path(logging_settings['log_file'])
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=logging_settings['max_log_size'],
                backupCount=logging_settings['backup_count']
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        logger = logging.getLogger('x_scraper')
        return logger
    
    def _initialize_components(self) -> None:
        try:
            credentials = self.config_manager.get_twitter_credentials()
            
            if not credentials.get('username'):
                self.logger.error("No Twitter account configured in config.ini")
                raise RuntimeError("Please configure a Twitter account in [TWITTER] section")
            
            username = credentials['username']
            email = credentials['email']
            password = credentials['password']
            
            self.twitter_session = TwitterSession(
                username=username,
                email=email,
                password=password,
                twitter_settings={}
            )
            self.logger.info(f"Initialized Twitter session for @{username}")
            
            
            proxy_settings = self.config_manager.get_proxy_settings()
            
            
            ai_settings = self.config_manager.get_ai_settings()
            if ai_settings.get('openai_api_key'):
                self.ai_analyzer = AIAnalyzer(
                    api_key=ai_settings['openai_api_key'],
                    model=ai_settings['model'],
                    max_tokens=ai_settings['max_tokens'],
                    temperature=ai_settings['temperature']
                )
                self.logger.info("Initialized AI analyzer with OpenAI")
            else:
                self.logger.warning("AI analyzer not initialized - missing OpenAI API key")
            
            
            self.progress_manager = ProgressManager()
            self.logger.info("Initialized progress manager")
            
            
            self.proxy_settings = proxy_settings
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise
    
    async def login(self) -> bool:
        
        try:
            if not self.twitter_session:
                self.logger.error("Twitter session not initialized")
                return False
            
            if self.playwright_scraper is None:
                
                creds = self.twitter_session.get_credentials()
                
                
                self.playwright_scraper = PlaywrightScraper(
                    username=creds['username'],
                    password=creds['password'],
                    email=creds['email'],
                    scraping_config=self.config_manager.get_scraping_settings(),
                    timeout_config=self.config_manager.get_timeout_settings(),
                    proxy_config=self.proxy_settings if self.proxy_settings.get('enable_proxy_rotation') else None,
                    progress_manager=self.progress_manager
                )
                
                
                if not await self.playwright_scraper.initialize():
                    self.logger.error("Failed to initialize Playwright browser")
                    return False
                
                
                if await self.playwright_scraper.login():
                    self.twitter_session.mark_logged_in()
                    self.logger.info("Successfully logged in with Playwright")
                    return True
                else:
                    self.logger.error("Login failed")
                    return False
            else:
                
                if self.twitter_session.is_logged_in:
                    return True
                else:
                    return await self.playwright_scraper.login()
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False
    
    async def search_tweets(self, query: str, count: Optional[int] = None, 
                          result_type: Optional[str] = None, analyze: bool = True,
                          analysis_types: Optional[List[str]] = None) -> Dict[str, Any]:
        
        scraping_settings = self.config_manager.get_scraping_settings()
        max_tweets = count or scraping_settings.get('default_tweet_count', 50)
        result_type = result_type or "Latest"
        
        self.session_stats['start_time'] = time.time()
        self.is_running = True
        
        try:
            if not self.playwright_scraper or not self.twitter_session or not self.twitter_session.is_logged_in:
                if not await self.login():
                    raise RuntimeError("Failed to login before searching")
            
            if not self.playwright_scraper:
                raise RuntimeError("Playwright scraper not initialized")
            
            self.logger.info(f"Searching for: '{query}' (type: {result_type}, limit: {max_tweets})")
            
            search_result = await self.playwright_scraper.search_tweets(
                query=query,
                max_tweets=max_tweets,
                result_type=result_type
            )
            
            if 'error' in search_result:
                self.logger.error(f"Search error: {search_result['error']}")
                return search_result
            
            tweets = search_result.get('tweets', [])
            self.scraped_tweets.extend(tweets)
            self.session_stats['tweets_scraped'] += len(tweets)
            
            result = {
                'query': query,
                'tweet_count': len(tweets),
                'tweets': tweets,
                'scraped_at': time.time(),
                'analysis': None
            }
            
            filtered_tweets = self._apply_filters(tweets)
            result['filtered_tweet_count'] = len(filtered_tweets)
            result['tweets'] = filtered_tweets
            
            if analyze and self.ai_analyzer and filtered_tweets:
                self.logger.info("Starting AI analysis...")
                analysis_result = await self._analyze_tweets(
                    filtered_tweets,
                    analysis_types or ['sentiment', 'topics', 'summary']
                )
                result['analysis'] = analysis_result
                self.session_stats['analyses_performed'] += 1
            
            self.logger.info(f"Search completed: {len(filtered_tweets)} tweets found for '{query}'")
            return result
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            self.session_stats['errors_encountered'] += 1
            raise
        finally:
            self.is_running = False
            self.session_stats['end_time'] = time.time()
    
    async def scrape_user_tweets(self, username: str, count: Optional[int] = None,
                                analyze: bool = True, analysis_types: Optional[List[str]] = None,
                                unlimited_history: bool = True, browser_mode: bool = True,
                                resume: bool = False, max_tweets_per_session: Optional[int] = None) -> Dict[str, Any]:

        
        scraping_settings = self.config_manager.get_scraping_settings()
        
        if max_tweets_per_session is None:
            config_limit = scraping_settings.get('max_tweets_per_session', 0)
            max_tweets_per_session = config_limit if config_limit > 0 else None
        
        checkpoint = None
        existing_tweets = []
        resume_from_tweet_id = None
        
        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint(username)
            if checkpoint:
                existing_tweets = self.checkpoint_manager.load_existing_tweets(username)
                resume_from_tweet_id = checkpoint.get('oldest_tweet_id')
                existing_tweet_ids = {tweet.get('id') for tweet in existing_tweets if tweet.get('id')}
                self.logger.info(f"Resuming from checkpoint with {len(existing_tweets)} existing tweets")
                self.logger.info(f"   Will continue from tweet: {resume_from_tweet_id}")
                self.logger.info(f"   Tracking {len(existing_tweet_ids)} existing tweet IDs")
            else:
                self.logger.info(f"No checkpoint found for @{username}, starting fresh")
                existing_tweet_ids = set()
        else:
            self.logger.info(f"Starting fresh scrape for @{username}")
            existing_tweet_ids = set()
        
        self.session_stats['start_time'] = time.time()
        self.is_running = True
        
        try:

            if not self.playwright_scraper or not self.twitter_session or not self.twitter_session.is_logged_in:
                if not await self.login():
                    raise RuntimeError("Failed to login before scraping")
            

            if not self.playwright_scraper:
                raise RuntimeError("Playwright scraper not initialized")
            
            scrape_result = await self.playwright_scraper.scrape_user_tweets(
                username, 
                resume_from_tweet_id=resume_from_tweet_id,
                max_tweets_per_session=max_tweets_per_session,
                existing_tweet_ids=existing_tweet_ids
            )
            
            if 'error' in scrape_result:
                self.logger.error(f"Scraping error: {scrape_result['error']}")
                return scrape_result
            
            new_tweets = scrape_result.get('tweets', [])
            user_data = scrape_result.get('user_data')
            
            if resume:
                self.logger.info(f"Resume session completed: {len(new_tweets)} NEW (older) tweets collected")
            else:
                self.logger.info(f"Fresh scraping completed: {len(new_tweets)} tweets collected")
            
            if existing_tweets:
                self.logger.info(f"Merging: {len(existing_tweets)} existing + {len(new_tweets)} new tweets")
                all_tweets = self.checkpoint_manager.merge_tweets(existing_tweets, new_tweets)
                self.logger.info(f"Total tweets after merge: {len(all_tweets)}")
            else:
                all_tweets = new_tweets
                self.logger.info(f"No existing tweets to merge, total: {len(all_tweets)}")
            
            self.scraped_tweets.extend(new_tweets)
            self.session_stats['tweets_scraped'] += len(new_tweets)
            
            if all_tweets:
                sorted_by_id = sorted(
                    all_tweets,
                    key=lambda x: int(x.get('id', '0')) if x.get('id', '').isdigit() else 0
                )
                oldest_tweet = sorted_by_id[0] if sorted_by_id else None 
                newest_tweet = sorted_by_id[-1] if sorted_by_id else None 
                
                session_number = (checkpoint.get('session_count', 0) + 1) if checkpoint else 1
                
                checkpoint_data = {
                    'total_tweets': len(all_tweets),
                    'oldest_tweet_id': oldest_tweet.get('id') if oldest_tweet else None,
                    'oldest_tweet_date': oldest_tweet.get('created_at') if oldest_tweet else None,
                    'newest_tweet_id': newest_tweet.get('id') if newest_tweet else None,
                    'newest_tweet_date': newest_tweet.get('created_at') if newest_tweet else None,
                    'session_count': session_number,
                    'last_session_tweets': len(new_tweets)
                }
                
                self.logger.info(f"Saving checkpoint for session #{session_number}:")
                self.logger.info(f"   • This session: {len(new_tweets)} new tweets")
                self.logger.info(f"   • Total collected: {len(all_tweets)} tweets")
                self.logger.info(f"   • Oldest tweet: {checkpoint_data['oldest_tweet_date']}")
                
                self.checkpoint_manager.save_checkpoint(username, checkpoint_data)
                
                
                self.checkpoint_manager.save_all_tweets(username, all_tweets, user_data, checkpoint_data)
            
            tweets = all_tweets  
            
            result = {
                'username': username,
                'user_data': user_data,
                'tweet_count': len(tweets),
                'tweets': tweets,
                'scraped_at': time.time(),
                'analysis': None
            }
            
            
            filtered_tweets = self._apply_filters(tweets)
            result['filtered_tweet_count'] = len(filtered_tweets)
            result['tweets'] = filtered_tweets
            
            
            if analyze and self.ai_analyzer and filtered_tweets:
                self.logger.info("Starting AI analysis...")
                analysis_result = await self._analyze_tweets(
                    filtered_tweets,
                    analysis_types or ['sentiment', 'topics', 'summary']
                )
                result['analysis'] = analysis_result
                self.session_stats['analyses_performed'] += 1
            
            
            self.logger.info(f"Scraping completed: {len(filtered_tweets)} tweets retrieved")
            self.logger.info(f"All data saved to data/{username}/tweets_{username}.json")
            return result
            
        except Exception as e:
            self.logger.error(f"User tweet scraping failed: {str(e)}")
            self.session_stats['errors_encountered'] += 1
            raise
        finally:
            self.is_running = False
            self.session_stats['end_time'] = time.time()
    
    async def scrape_user_tweets_by_search(self, username: str, since_date: str, until_date: str,
                                           max_tweets_per_range: Optional[int] = None,
                                           existing_tweet_ids: Optional[set] = None) -> Dict[str, Any]:
        self.session_stats['start_time'] = time.time()
        self.is_running = True
        
        try:
            if not self.playwright_scraper or not self.twitter_session or not self.twitter_session.is_logged_in:
                if not await self.login():
                    raise RuntimeError("Failed to login before scraping")
            
            if not self.playwright_scraper:
                raise RuntimeError("Playwright scraper not initialized")
            
            scrape_result = await self.playwright_scraper.scrape_user_tweets_by_search(
                username=username,
                since_date=since_date,
                until_date=until_date,
                max_tweets_per_range=max_tweets_per_range,
                existing_tweet_ids=existing_tweet_ids
            )
            
            if 'error' in scrape_result:
                self.logger.error(f"Search scraping error: {scrape_result['error']}")
                return scrape_result
            
            tweets = scrape_result.get('tweets', [])
            self.scraped_tweets.extend(tweets)
            self.session_stats['tweets_scraped'] += len(tweets)
            
            return scrape_result
            
        except Exception as e:
            self.logger.error(f"Search-based scraping failed: {str(e)}")
            self.session_stats['errors_encountered'] += 1
            raise
        finally:
            self.is_running = False
            self.session_stats['end_time'] = time.time()
    
    def _apply_filters(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filter_settings = self.config_manager.get_filter_settings()
        filtered_tweets = []
        
        for tweet in tweets:
            user_followers = tweet.get('user', {}).get('followers_count', 0)
            if user_followers < filter_settings['min_followers']:
                continue
            
            if filter_settings['verified_only']:
                user_verified = tweet.get('user', {}).get('verified', False)
                if not user_verified:
                    continue
            
            if filter_settings['exclude_retweets'] and tweet.get('is_retweet', False):
                continue
            
            
            if filter_settings['exclude_replies'] and tweet.get('is_reply', False):
                continue
            
            
            tweet_lang = tweet.get('lang', 'en')
            allowed_languages = filter_settings['language']
            if allowed_languages:
                if ',' in allowed_languages:
                    allowed_langs = [lang.strip() for lang in allowed_languages.split(',')]
                    if tweet_lang not in allowed_langs:
                        continue
                else:
                    if tweet_lang != allowed_languages:
                        continue
            
            filtered_tweets.append(tweet)
        
        self.logger.info(f"Applied filters: {len(tweets)} -> {len(filtered_tweets)} tweets")
        return filtered_tweets
    
    async def _analyze_tweets(self, tweets: List[Dict[str, Any]], 
                            analysis_types: List[str]) -> Dict[str, Any]:
        try:
            analysis_enums = []
            for analysis_type in analysis_types:
                try:
                    analysis_enums.append(AnalysisType(analysis_type.lower()))
                except ValueError:
                    self.logger.warning(f"Unknown analysis type: {analysis_type}")
            
            if not analysis_enums:
                return {"error": "No valid analysis types provided"}
            
            self.logger.info(f"Performing AI analysis on {len(tweets)} tweets")
            
            if not self.ai_analyzer:
                return {"error": "AI analyzer not initialized"}
            
            analysis_result = await self.ai_analyzer.analyze_tweets(
                tweets=tweets,
                analysis_types=analysis_enums
            )
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"AI analysis failed: {str(e)}")
            return {"error": str(e)}
    
    async def _save_results(self, results: Dict[str, Any], filename_prefix: str) -> None:  
        try:
            scraping_settings = self.config_manager.get_scraping_settings()
            base_output_dir = Path(scraping_settings['output_directory'])
            output_format = scraping_settings.get('output_format', 'json')
            
            
            username = None
            if 'username' in results:
                username = results['username']
            elif filename_prefix.startswith('user_'):
                username = filename_prefix.replace('user_', '')
            elif filename_prefix.startswith('search_'):
                username = 'search_results'
            else:
                username = 'general'
            
            user_output_dir = base_output_dir / username
            user_output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            
            tweets_data = {
                'username': results.get('username'),
                'user_data': results.get('user_data'),
                'tweet_count': results.get('tweet_count'),
                'filtered_tweet_count': results.get('filtered_tweet_count'),
                'tweets': results.get('tweets', []),
                'scraped_at': results.get('scraped_at'),
                'query': results.get('query')
            }
            
            save_tasks = []
            
            tweets_filename = f"tweets_{timestamp}"
            
            
            if output_format == 'json' or output_format == 'all':
                tweets_filepath = user_output_dir / f"{tweets_filename}.json"
                
                async def save_tweets_json():
                    async with aiofiles.open(tweets_filepath, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(tweets_data, indent=2, default=str))
                    self.logger.info(f"Tweets saved to: {tweets_filepath}")
                
                save_tasks.append(save_tweets_json())
            

            if output_format == 'csv' or output_format == 'all':
                tweets_csv_path = user_output_dir / f"{tweets_filename}.csv"
                
                async def save_tweets_csv():
                    tweets_list = results.get('tweets', [])
                    if tweets_list:
                        flattened_tweets = []
                        for tweet in tweets_list:
                            flat_tweet = {
                                'id': tweet.get('id'),
                                'text': tweet.get('text', ''),
                                'created_at': tweet.get('created_at'),
                                'username': tweet.get('user', {}).get('username', ''),
                                'display_name': tweet.get('user', {}).get('display_name', ''),
                                'followers_count': tweet.get('user', {}).get('followers_count', 0),
                                'verified': tweet.get('user', {}).get('verified', False),
                                'retweet_count': tweet.get('metrics', {}).get('retweet_count', 0),
                                'favorite_count': tweet.get('metrics', {}).get('favorite_count', 0),
                                'reply_count': tweet.get('metrics', {}).get('reply_count', 0),
                                'view_count': tweet.get('metrics', {}).get('view_count', 0),
                                'is_retweet': tweet.get('is_retweet', False),
                                'is_reply': tweet.get('is_reply', False),
                                'lang': tweet.get('lang', ''),
                                'hashtags': ', '.join(tweet.get('hashtags', [])),
                                'scraped_at': tweet.get('scraped_at')
                            }
                            flattened_tweets.append(flat_tweet)
                        
                        df = pd.DataFrame(flattened_tweets)
                        df.to_csv(tweets_csv_path, index=False, encoding='utf-8')
                        self.logger.info(f"Tweets saved to CSV: {tweets_csv_path}")
                
                save_tasks.append(save_tweets_csv())
            
            
            if results.get('analysis'):
                ai_dir = user_output_dir / 'ai_analysis'
                ai_dir.mkdir(exist_ok=True)
                
                analysis_filename = f"analysis_{timestamp}.json"
                analysis_filepath = ai_dir / analysis_filename
                
                analysis_data = {
                    'username': results.get('username'),
                    'query': results.get('query'),
                    'tweet_count': results.get('tweet_count'),
                    'analysis_timestamp': timestamp,
                    'analysis': results.get('analysis')
                }
                
                async def save_analysis_data():
                    async with aiofiles.open(analysis_filepath, 'w', encoding='utf-8') as f:
                        await f.write(json.dumps(analysis_data, indent=2, default=str))
                    self.logger.info(f"AI analysis saved to: {analysis_filepath}")
                
                save_tasks.append(save_analysis_data())
            
            
            if save_tasks:
                start_time = time.time()
                await asyncio.gather(*save_tasks)
                save_time = time.time() - start_time
                self.logger.info(f"File operations completed in {save_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        stats = self.session_stats.copy()
        
        if stats['start_time'] and stats['end_time']:
            stats['duration'] = stats['end_time'] - stats['start_time']
        elif stats['start_time']:
            stats['duration'] = time.time() - stats['start_time']
        
        
        if self.ai_analyzer:
            stats['ai_cache_stats'] = self.ai_analyzer.get_cache_stats()
        
        
        if self.twitter_session:
            stats['session_info'] = self.twitter_session.get_session_info()
        
        return stats
    
    async def refresh_twitter_session(self) -> bool:
        try:
            if self.playwright_scraper:
                
                return await self.login()
            return False
        except Exception as e:
            self.logger.error(f"Session refresh failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        try:
            if self.playwright_scraper:
                await self.playwright_scraper.cleanup()
            
            if self.ai_analyzer:
                self.ai_analyzer.clear_cache()
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")