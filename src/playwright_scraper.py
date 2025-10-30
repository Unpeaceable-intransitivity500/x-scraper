import asyncio
import logging
import json
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import urllib.parse
from playwright.async_api import async_playwright, Page, Response, Browser, BrowserContext
from .exceptions import PageLoadError
from .decorators import retry_on_network_error

try:
    import jmespath  # type: ignore
except ImportError:
    jmespath = None  # type: ignore


class PlaywrightScraper:
    def __init__(self, username: str, password: str, email: str, scraping_config: Dict, timeout_config: Dict, proxy_config: Optional[Dict] = None, progress_manager=None):
        self.username = username
        self.password = password
        self.email = email
        self.proxy_config = proxy_config
        self.progress_manager = progress_manager
        self.logger = logging.getLogger(__name__)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None 
        self.scraped_tweet_ids = set()
        self.all_tweets = []
        self.user_data = None
        self.captured_requests = []
        self.cookies_file = "playwright_cookies.json"
        self.is_logged_in = False     
        self.current_username = None
        self.start_time: Optional[float] = None
        self.scroll_delay_min = scraping_config['scroll_delay_min']
        self.scroll_delay_max = scraping_config['scroll_delay_max']
        self.max_scroll_attempts = scraping_config['max_scroll_attempts']
        self.scroll_attempts_without_new = 0
        self.max_attempts_without_new = scraping_config['max_attempts_without_new']
        self.max_tweets_per_session = None
        self.overlap_threshold = scraping_config['overlap_detection_threshold']
        self.timeouts = timeout_config
        
        self.logger.info("Playwright scraper initialized")
    
    async def initialize(self): 
        try:
            self.playwright = await async_playwright().start()
            
            browser_args = {
                'headless': False, 
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                ]
            }
            
            if self.proxy_config and self.proxy_config.get('enable_proxy_rotation'):
                proxy_list = self.proxy_config.get('proxies', [])
                if proxy_list:
                    proxy_str = proxy_list[0]
                    parts = proxy_str.split(':')
                    if len(parts) == 4:
                        host, port, username, password = parts
                        browser_args['proxy'] = {
                            'server': f'http://{host}:{port}',
                            'username': username,
                            'password': password
                        }
                        self.logger.info(f"Using proxy: {username}@{host}:{port}")
                        self.logger.info("Note: First connection through proxy may take 30-60 seconds...")
            
            self.browser = await self.playwright.chromium.launch(**browser_args)
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            cookies_loaded = False
            if Path(self.cookies_file).exists():
                try:
                    cookies_data = json.loads(Path(self.cookies_file).read_text())
                    if cookies_data:  
                        await self.context.add_cookies(cookies_data)
                        self.logger.info("Loaded saved cookies - will skip login")
                        self.is_logged_in = True 
                        cookies_loaded = True
                except Exception as e:
                    self.logger.warning(f"Failed to load cookies: {e}")
            
            if not cookies_loaded:
                self.logger.info("No saved cookies found - will need to login")
            
            self.page = await self.context.new_page()
            
            
            self.page.on("response", self._intercept_response)
            
            self.logger.info("Playwright browser initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Playwright: {e}")
            return False
    
    async def _intercept_response(self, response: Response):
        try:
            
            if response.request.resource_type in ["xhr", "fetch"]:
                url = response.url
                
                if 'graphql' in url.lower() or 'api.twitter.com' in url or 'api.x.com' in url:
                    if '/' in url:
                        parts = url.split('/')
                        for i, part in enumerate(parts):
                            if 'graphql' in part.lower() and i + 1 < len(parts):
                                operation = parts[i + 1].split('?')[0]
                                self.logger.debug(f"GraphQL: {operation}")
                                break
                
                
                if any(endpoint in url for endpoint in [
                    'UserByScreenName',
                    'UserTweets',
                    'TweetDetail',
                    'TweetResultByRestId',
                    'SearchTimeline',
                    'SearchAdaptive'
                ]):
                    try:
                        data = await response.json()
                        self.captured_requests.append({
                            'url': url,
                            'data': data,
                            'timestamp': time.time()
                        })
                        
                        
                        if 'UserByScreenName' in url:
                            self.logger.info("Parsing UserByScreenName response")
                            self._parse_user_data(data)
                        elif 'UserTweets' in url:
                            self.logger.info("Parsing UserTweets response")
                            self._parse_tweets_from_timeline(data)
                        elif 'SearchTimeline' in url or 'SearchAdaptive' in url:
                            self.logger.info("Parsing Search response")
                            self._parse_tweets_from_timeline(data)
                        elif 'TweetResultByRestId' in url or 'TweetDetail' in url:
                            self.logger.info("Parsing TweetDetail response")
                            self._parse_single_tweet(data)
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to parse response from {url[:100]}: {e}")
                        
        except Exception as e:
            self.logger.debug(f"Error in response interceptor: {e}")
    
    def _parse_user_data(self, data: Dict):
        if not jmespath:
            self.logger.warning("jmespath not available, skipping user data parsing")
            return
            
        try:
            
            user_result = jmespath.search('data.user.result', data)
            if user_result:
                legacy = user_result.get('legacy', {})
                self.user_data = {
                    'id': user_result.get('rest_id', ''),
                    'username': legacy.get('screen_name', ''),
                    'display_name': legacy.get('name', ''),
                    'bio': legacy.get('description', ''),
                    'followers_count': legacy.get('followers_count', 0),
                    'following_count': legacy.get('friends_count', 0),
                    'tweet_count': legacy.get('statuses_count', 0),
                    'verified': user_result.get('is_blue_verified', False) or legacy.get('verified', False),
                    'profile_image_url': legacy.get('profile_image_url_https', ''),
                    'profile_banner_url': legacy.get('profile_banner_url', ''),
                    'created_at': legacy.get('created_at', ''),
                    'location': legacy.get('location', ''),
                    'url': legacy.get('url', ''),
                }
                self.logger.info(f"Captured user data: @{self.user_data['username']} ({self.user_data['followers_count']} followers)")
        except Exception as e:
            self.logger.error(f"Error parsing user data: {e}")
    
    def _parse_tweets_from_timeline(self, data: Dict):
        if not jmespath:
            self.logger.warning("jmespath not available, skipping tweet parsing")
            return
            
        try:
            self.logger.debug(f"Parsing timeline data structure...")
            
            instructions = jmespath.search('data.user.result.timeline_v2.timeline.instructions', data)
            if not instructions:
                instructions = jmespath.search('data.user.result.timeline.timeline.instructions', data)
            if not instructions:
                instructions = jmespath.search('data.search_by_raw_query.search_timeline.timeline.instructions', data)
            if not instructions:
                instructions = jmespath.search('data.threaded_conversation_with_injections_v2.instructions', data)
            
            if not instructions:
                self.logger.warning("No timeline instructions found in any known format")
                self.logger.debug(f"Available data keys: {list(data.get('data', {}).keys()) if 'data' in data else 'no data key'}")
                return
            
            self.logger.debug(f"Found {len(instructions)} instructions")
            
            for instruction in instructions:
                instruction_type = instruction.get('type')
                self.logger.debug(f"Processing instruction type: {instruction_type}")
                
                if instruction_type == 'TimelineAddEntries':
                    entries = instruction.get('entries', [])
                    self.logger.info(f"Found {len(entries)} entries in timeline")
                    
                    tweet_count = 0
                    skipped_entries = []
                    all_entry_ids = []
                    for entry in entries:
                        entry_id = entry.get('entryId', '')
                        all_entry_ids.append(entry_id)
                        
                        if any(skip_type in entry_id for skip_type in ['cursor-', 'who-to-follow', 'profile-conversation']):
                            skipped_entries.append(entry_id)
                            continue
                        
                        tweet_result = jmespath.search('content.itemContent.tweet_results.result', entry)
                        if tweet_result:
                            parsed_tweet = self._extract_tweet_data(tweet_result)
                            tweet_id = parsed_tweet.get('id') if parsed_tweet else None
                            if parsed_tweet and tweet_id:
                                if tweet_id not in self.scraped_tweet_ids:
                                    if not hasattr(self, 'existing_tweet_ids') or tweet_id not in self.existing_tweet_ids:
                                        self.all_tweets.append(parsed_tweet)
                                        self.scraped_tweet_ids.add(tweet_id)
                                        tweet_count += 1
                    
                    if tweet_count > 0:
                        self.logger.info(f"Extracted {tweet_count} tweets from this batch")
                    else:
                        self.logger.warning(f"No tweets extracted from {len(entries)} entries")
                        if all_entry_ids:
                            self.logger.debug(f"All entry IDs: {all_entry_ids[:10]}")
                        if skipped_entries:
                            self.logger.debug(f"Skipped entry IDs: {skipped_entries[:5]}")  
                                
        except Exception as e:
            self.logger.error(f"Error parsing timeline tweets: {e}", exc_info=True)
    
    def _parse_single_tweet(self, data: Dict):
        if not jmespath:
            return
            
        try:
            tweet_result = jmespath.search('data.tweetResult.result', data)
            if tweet_result:
                parsed_tweet = self._extract_tweet_data(tweet_result)
                tweet_id = parsed_tweet.get('id') if parsed_tweet else None
                
                if parsed_tweet and tweet_id and tweet_id not in self.scraped_tweet_ids:
                    if not hasattr(self, 'existing_tweet_ids') or tweet_id not in self.existing_tweet_ids:
                        self.all_tweets.append(parsed_tweet)
                        self.scraped_tweet_ids.add(tweet_id)
        except Exception as e:
            self.logger.error(f"Error parsing single tweet: {e}")
    
    def _extract_tweet_data(self, tweet_result: Dict) -> Optional[Dict[str, Any]]:
        try:
            
            if tweet_result.get('__typename') == 'TweetWithVisibilityResults':
                tweet_result = tweet_result.get('tweet', {})
            
            legacy = tweet_result.get('legacy', {})
            tweet_id = tweet_result.get('rest_id', '')
            
            
            user_result = tweet_result.get('core', {}).get('user_results', {}).get('result', {})
            user_legacy = user_result.get('legacy', {})
            
            
            media = []
            extended_entities = legacy.get('extended_entities', {})
            for media_item in extended_entities.get('media', []):
                media_info = {
                    'type': media_item.get('type', ''),
                    'url': media_item.get('media_url_https', ''),
                    'expanded_url': media_item.get('expanded_url', '')
                }
                if media_item.get('type') == 'video':
                    variants = media_item.get('video_info', {}).get('variants', [])
                    
                    video_variants = [v for v in variants if v.get('content_type') == 'video/mp4']
                    if video_variants:
                        media_info['video_url'] = max(video_variants, key=lambda x: x.get('bitrate', 0))['url']
                media.append(media_info)
            
            
            urls = []
            for url_entity in legacy.get('entities', {}).get('urls', []):
                urls.append({
                    'url': url_entity.get('url', ''),
                    'expanded_url': url_entity.get('expanded_url', ''),
                    'display_url': url_entity.get('display_url', '')
                })
            
            hashtags = [ht.get('text', '') for ht in legacy.get('entities', {}).get('hashtags', [])]
            
            
            tweet_data = {
                'id': tweet_id,
                'text': legacy.get('full_text', ''),
                'full_text': legacy.get('full_text', ''),
                'created_at': legacy.get('created_at', ''),
                'user': {
                    'id': user_result.get('rest_id', ''),
                    'username': user_legacy.get('screen_name', ''),
                    'display_name': user_legacy.get('name', ''),
                    'followers_count': user_legacy.get('followers_count', 0),
                    'following_count': user_legacy.get('friends_count', 0),
                    'verified': user_result.get('is_blue_verified', False) or user_legacy.get('verified', False),
                    'profile_image_url': user_legacy.get('profile_image_url_https', ''),
                    'description': user_legacy.get('description', '')
                },
                'metrics': {
                    'retweet_count': legacy.get('retweet_count', 0),
                    'favorite_count': legacy.get('favorite_count', 0),
                    'reply_count': legacy.get('reply_count', 0),
                    'quote_count': legacy.get('quote_count', 0),
                    'view_count': tweet_result.get('views', {}).get('count', 0)
                },
                'lang': legacy.get('lang', 'en'),
                'possibly_sensitive': legacy.get('possibly_sensitive', False),
                'is_retweet': legacy.get('retweeted', False),
                'is_reply': legacy.get('in_reply_to_status_id_str') is not None,
                'is_quote': legacy.get('is_quote_status', False),
                'hashtags': hashtags,
                'urls': urls,
                'media': media,
                'scraped_at': time.time()
            }
            
            return tweet_data
            
        except Exception as e:
            self.logger.debug(f"Error extracting tweet data: {e}")
            return None
    
    async def login(self) -> bool:
        if not self.page or not self.context:
            raise RuntimeError("Browser not initialized")
        
        try:
            
            if self.is_logged_in:
                self.logger.info("Already logged in with saved cookies - skipping login")
                
                try:
                    await self.page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=self.timeouts['element_wait_timeout'])
                    
                    self.logger.info("Verifying cookies... (waiting for page to fully load)")
                    try:
                        await self.page.wait_for_selector('[data-testid="SideNav_NewTweet_Button"]', timeout=self.timeouts['cookie_verification_timeout'])
                        self.logger.info("✓ Cookie login verified successfully")
                        return True
                    except:
                        current_url = self.page.url
                        if 'login' not in current_url and 'flow' not in current_url:
                            self.logger.info("✓ Cookies valid (on home page)")
                            return True
                        else:
                            self.logger.warning("Cookies expired, need to login again")
                            self.is_logged_in = False
                except Exception as e:
                    self.logger.warning(f"Cookie verification failed: {e}, will login")
                    self.is_logged_in = False
            
            self.logger.info("Attempting to login to Twitter (may take 30-60s through proxy)...")
            
            
            self.logger.info("Loading login page...")
            await self.page.goto('https://twitter.com/i/flow/login', 
                               wait_until='domcontentloaded', 
                               timeout=self.timeouts['page_load_timeout']) 
            
            
            await asyncio.sleep(self.timeouts['post_login_page_delay'])
            
            try:
                self.logger.info("Waiting for username input field...")
                username_input = await self.page.wait_for_selector('input[autocomplete="username"]', timeout=self.timeouts['element_wait_timeout'])
                if not username_input:
                    raise Exception("Username input field not found")
                self.logger.info("Username field found, entering credentials...")
                await username_input.fill(self.username)
                await asyncio.sleep(self.timeouts['post_input_delay'])
                
                
                self.logger.info("Clicking Next button (may take 30-60s through proxy)...")
                next_button = await self.page.wait_for_selector('button:has-text("Next")', timeout=self.timeouts['button_click_timeout'])
                if not next_button:
                    raise Exception("Next button not found")
                await next_button.click()
                await asyncio.sleep(self.timeouts['post_click_delay'])
            except Exception as e:
                self.logger.error(f"Failed to enter username: {e}")
                try:
                    await self.page.screenshot(path="login_error_username.png")
                    self.logger.info("Error screenshot saved: login_error_username.png")
                except:
                    pass
                return False
            
            
            try:
                
                self.logger.info("Checking for email verification...")
                email_input = await self.page.wait_for_selector('input[data-testid="ocfEnterTextTextInput"]', timeout=self.timeouts['short_wait_timeout'])
                if email_input:
                    self.logger.info("Email verification required")
                    await email_input.fill(self.email)
                    await asyncio.sleep(self.timeouts['post_input_delay'])
                    next_button = await self.page.wait_for_selector('button:has-text("Next")')
                    if next_button:
                        await next_button.click()
                        await asyncio.sleep(self.timeouts['post_click_delay'])
            except:
                self.logger.info("No email verification needed")
                pass  
            
            try:
                self.logger.info("Waiting for password input field...")
                password_input = await self.page.wait_for_selector('input[name="password"]', timeout=self.timeouts['element_wait_timeout'])
                if not password_input:
                    raise Exception("Password input field not found")
                self.logger.info("Password field found, entering password...")
                await password_input.fill(self.password)
                await asyncio.sleep(self.timeouts['post_input_delay'])
                
                
                self.logger.info("Clicking Login button...")
                login_button = await self.page.wait_for_selector('button[data-testid="LoginForm_Login_Button"]', timeout=self.timeouts['button_click_timeout'])
                if not login_button:
                    raise Exception("Login button not found")
                await login_button.click()
                self.logger.info("Waiting for login to complete...")
                await asyncio.sleep(self.timeouts['login_wait_delay'])
            except Exception as e:
                self.logger.error(f"Failed to enter password: {e}")
                try:
                    await self.page.screenshot(path="login_error_password.png")
                    self.logger.info("Error screenshot saved: login_error_password.png")
                except:
                    pass
                return False
            
            
            try:
                await self.page.wait_for_url('https://twitter.com/home', timeout=self.timeouts['login_complete_timeout'])
                self.is_logged_in = True
                
                
                cookies = await self.context.cookies()
                Path(self.cookies_file).write_text(json.dumps(cookies, indent=2))
                self.logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
                
                self.logger.info("Successfully logged in to Twitter")
                return True
            except:
                
                current_url = self.page.url
                self.logger.info(f"Current URL after login attempt: {current_url}")
                

                if any(indicator in current_url.lower() for indicator in ['home', 'x.com', 'twitter.com']):
                    try:
                        compose_button = await self.page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
                        if compose_button:
                            self.is_logged_in = True
                            cookies = await self.context.cookies()
                            Path(self.cookies_file).write_text(json.dumps(cookies, indent=2))
                            self.logger.info("Successfully logged in to Twitter")
                            return True
                    except:
                        pass
                    
                    
                    self.logger.warning("Logged in but couldn't verify home page - proceeding anyway")
                    self.is_logged_in = True
                    try:
                        cookies = await self.context.cookies()
                        Path(self.cookies_file).write_text(json.dumps(cookies, indent=2))
                        self.logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
                    except:
                        pass
                    return True
                else:
                    self.logger.error(f"Login failed - on URL: {current_url}")
                    
                    try:
                        await self.page.screenshot(path="login_failure.png")
                        self.logger.info("Screenshot saved to login_failure.png")
                    except:
                        pass
                    return False
                    
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False
    
    async def scrape_user_tweets(self, username: str, resume_from_tweet_id: Optional[str] = None, max_tweets_per_session: Optional[int] = None, existing_tweet_ids: Optional[set] = None) -> Dict[str, Any]:
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        try:
            self.current_username = username
            self.start_time = time.time()
            self.scraped_tweet_ids.clear()
            self.all_tweets.clear()
            self.user_data = None
            self.max_tweets_per_session = max_tweets_per_session
            self.existing_tweet_ids = existing_tweet_ids or set()  
            
            if resume_from_tweet_id:
                limit_info = f" (limit: {max_tweets_per_session} tweets)" if max_tweets_per_session else " (unlimited)"
                self.logger.info(f"Resuming scrape for @{username} from tweet {resume_from_tweet_id}{limit_info}")
                self.logger.info(f"   Tracking {len(self.existing_tweet_ids)} existing tweet IDs to avoid duplicates")
            else:
                limit_info = f" (limit: {max_tweets_per_session} tweets)" if max_tweets_per_session else " (unlimited)"
                self.logger.info(f"Starting scrape for @{username}{limit_info}")
            
            
            profile_url = f'https://twitter.com/{username}'
            await self.page.goto(profile_url, 
                               wait_until='domcontentloaded',
                               timeout=self.timeouts['page_load_timeout'])
            await asyncio.sleep(self.timeouts['post_navigation_delay'])
            
            
            try:
                error_element = await self.page.query_selector('text="This account doesn\'t exist"')
                if error_element:
                    self.logger.error(f"Account @{username} doesn't exist")
                    return {'error': 'Account not found', 'tweets': []}
            except:
                pass
            
            
            try:
                await self.page.wait_for_selector('[data-testid="tweet"]', timeout=self.timeouts['button_click_timeout'])
            except:
                self.logger.warning("No tweets found or page didn't load properly")
            
            
            await self._scroll_timeline(resume_from_tweet_id=resume_from_tweet_id, existing_tweet_ids=self.existing_tweet_ids)
            
            elapsed_time = time.time() - self.start_time
            self.logger.info(f"Scraping completed in {elapsed_time:.1f}s")
            self.logger.info(f"Total tweets collected: {len(self.all_tweets)}")
            
            return {
                'username': username,
                'user_data': self.user_data,
                'tweets': self.all_tweets,
                'tweet_count': len(self.all_tweets),
                'elapsed_time': elapsed_time
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping user tweets: {e}")
            return {'error': str(e), 'tweets': self.all_tweets}
    
    def _prepare_scraping_session(self, username: Optional[str] = None, max_tweets: Optional[int] = None, 
                                  existing_tweet_ids: Optional[set] = None) -> None:
        if username:
            self.current_username = username
        self.start_time = time.time()
        self.scraped_tweet_ids.clear()
        self.all_tweets.clear()
        self.user_data = None
        self.max_tweets_per_session = max_tweets
        self.existing_tweet_ids = existing_tweet_ids or set()
    
    @retry_on_network_error(max_retries=3, delay=10.0, exceptions=(Exception,))
    async def _navigate_with_retry(self, url: str, max_retries: int = 3) -> bool:
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        self.logger.info(f"Navigating to URL...")
        
        try:
            await self.page.goto(url, 
                               wait_until='domcontentloaded',
                               timeout=self.timeouts['page_load_timeout'])
            await asyncio.sleep(self.timeouts['post_navigation_delay'])
            return True
        except Exception as e:
            self.logger.error(f"Failed to navigate to {url}")
            raise PageLoadError(f"Navigation failed: {e}") from e
    
    async def _wait_for_tweets(self, timeout: Optional[int] = None) -> bool:
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        timeout = timeout or self.timeouts['button_click_timeout']
        try:
            await self.page.wait_for_selector('[data-testid="tweet"]', timeout=timeout)
            self.logger.info("Search results loaded successfully")
            return True
        except Exception:
            self.logger.warning("No tweets found in search results")
            return False
    
    def _build_search_url(self, username: Optional[str] = None, since_date: Optional[str] = None, until_date: Optional[str] = None, query: Optional[str] = None, result_type: str = "live") -> str:
        
        if query:
            search_query = query
        elif username and since_date and until_date:
            search_query = f"from:{username} since:{since_date} until:{until_date}"
        elif username:
            search_query = f"from:{username}"
        else:
            raise ValueError("Must provide either query or username")
        
        encoded_query = urllib.parse.quote(search_query)
        return f"https://twitter.com/search?q={encoded_query}&src=typed_query&f={result_type}"
    
    async def scrape_user_tweets_by_search(self, username: str, since_date: str, until_date: str, 
                                           max_tweets_per_range: Optional[int] = None,
                                           existing_tweet_ids: Optional[set] = None) -> Dict[str, Any]:
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        try:
            self._prepare_scraping_session(username, max_tweets_per_range, existing_tweet_ids)
            
            self.logger.info(f"Starting SEARCH scrape for @{username}")
            self.logger.info(f"   Date range: {since_date} to {until_date}")
            limit_info = f" (limit: {max_tweets_per_range} tweets)" if max_tweets_per_range else " (unlimited)"
            self.logger.info(f"   {limit_info}")
            
            search_url = self._build_search_url(username=username, since_date=since_date, until_date=until_date)
            await self._navigate_with_retry(search_url)
            
            if not await self._wait_for_tweets():
                return {
                    'username': username,
                    'user_data': None,
                    'tweets': [],
                    'tweet_count': 0,
                    'elapsed_time': 0,
                    'date_range': {'since': since_date, 'until': until_date}
                }
            
            await self._scroll_timeline(resume_from_tweet_id=None, existing_tweet_ids=self.existing_tweet_ids)
            
            elapsed_time: float = time.time() - (self.start_time or 0)
            self.logger.info(f"Search scraping completed in {elapsed_time:.1f}s")
            self.logger.info(f"Total tweets collected from {since_date} to {until_date}: {len(self.all_tweets)}")
            
            return {
                'username': username,
                'user_data': self.user_data,
                'tweets': self.all_tweets,
                'tweet_count': len(self.all_tweets),
                'elapsed_time': elapsed_time,
                'date_range': {'since': since_date, 'until': until_date}
            }
            
        except Exception as e:
            self.logger.error(f"Error in search scraping: {e}")
            return {
                'error': str(e), 
                'tweets': self.all_tweets,
                'date_range': {'since': since_date, 'until': until_date}
            }
    
    async def search_tweets(self, query: str, max_tweets: Optional[int] = None, result_type: str = "Latest") -> Dict[str, Any]:
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        try:
            self._prepare_scraping_session(username=None, max_tweets=max_tweets, existing_tweet_ids=set())
            
            result_type_map = {
                "Latest": "live",
                "Top": "top",
                "Media": "image"
            }
            search_type = result_type_map.get(result_type, "live")
            
            self.logger.info(f"Starting KEYWORD search for: '{query}'")
            limit_info = f" (limit: {max_tweets} tweets)" if max_tweets else " (unlimited)"
            self.logger.info(f"   Result type: {result_type}{limit_info}")
            
            search_url = self._build_search_url(query=query, result_type=search_type)
            await self._navigate_with_retry(search_url)
            
            if not await self._wait_for_tweets():
                return {
                    'query': query,
                    'user_data': None,
                    'tweets': [],
                    'tweet_count': 0,
                    'elapsed_time': 0
                }
            
            await self._scroll_timeline(resume_from_tweet_id=None, existing_tweet_ids=set())
            
            elapsed_time: float = time.time() - (self.start_time or 0)
            self.logger.info(f"Search completed in {elapsed_time:.1f}s")
            self.logger.info(f"Total tweets collected for '{query}': {len(self.all_tweets)}")
            
            return {
                'query': query,
                'user_data': None,
                'tweets': self.all_tweets,
                'tweet_count': len(self.all_tweets),
                'elapsed_time': elapsed_time
            }
            
        except Exception as e:
            self.logger.error(f"Error in keyword search: {e}")
            return {
                'error': str(e), 
                'query': query,
                'tweets': self.all_tweets
            }
    
    async def _scroll_timeline(self, resume_from_tweet_id: Optional[str] = None, existing_tweet_ids: Optional[set] = None):
        if not self.page:
            raise RuntimeError("Browser not initialized")
            
        self.logger.info("Starting timeline scroll...")
        
        scroll_attempts = 0
        self.scroll_attempts_without_new = 0
        resume_point_found = False if resume_from_tweet_id else True
        existing_tweet_ids = existing_tweet_ids or set() 
        
        while scroll_attempts < self.max_scroll_attempts:
            scroll_attempts += 1
            tweets_before = len(self.all_tweets)
            
            
            await self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
            
            
            delay = random.uniform(self.scroll_delay_min, self.scroll_delay_max)
            await asyncio.sleep(delay)
            
            
            tweets_after = len(self.all_tweets)
            new_tweets = tweets_after - tweets_before
            
            
            if resume_from_tweet_id and not resume_point_found and existing_tweet_ids:
                overlap_count = sum(1 for tweet in self.all_tweets if tweet.get('id') in existing_tweet_ids)
                
                if overlap_count >= self.overlap_threshold:  
                    resume_point_found = True
                    self.logger.info(f"Found overlap zone! Detected {overlap_count} existing tweets")
                    self.logger.info(f"   Clearing {len(self.all_tweets)} tweets (duplicates + recent)...")
                    self.logger.info(f"   Now collecting OLDER tweets (before previous session)...")
                    
                    self.all_tweets.clear()
                    self.scraped_tweet_ids.clear()
                    
                    tweets_before = 0
                    tweets_after = 0
                    new_tweets = 0
                    self.scroll_attempts_without_new = 0
            
            if new_tweets > 0:
                if not resume_point_found:
                    self.logger.info(f"Scrolling to resume point... ({tweets_after} tweets checked)")
                else:
                    if self.max_tweets_per_session:
                        progress_pct = (tweets_after / self.max_tweets_per_session) * 100
                        self.logger.info(f"Scroll {scroll_attempts}: +{new_tweets} NEW tweets (total: {tweets_after}/{self.max_tweets_per_session}, {progress_pct:.1f}%)")
                    else:
                        self.logger.info(f"Scroll {scroll_attempts}: +{new_tweets} NEW tweets (total: {tweets_after})")
                self.scroll_attempts_without_new = 0
            else:
                self.scroll_attempts_without_new += 1
                
                if scroll_attempts >= 20 and len(self.all_tweets) == 0:
                    self.logger.error("Scrolled 20 times with 0 tweets extracted - tweet parsing is broken!")
                    self.logger.error("   Check the debug logs for skipped entry IDs")
                    break
                
                if not resume_point_found and self.scroll_attempts_without_new >= 100:
                    self.logger.warning(f"Scrolled 100 times without finding resume point - might not exist")
                    break
                elif resume_point_found and self.scroll_attempts_without_new >= self.max_attempts_without_new:
                    self.logger.info(f"No new tweets for {self.max_attempts_without_new} scrolls - stopping")
                    break
            
            if resume_point_found and self.max_tweets_per_session and len(self.all_tweets) >= self.max_tweets_per_session:
                self.logger.info(f"Session limit reached: {len(self.all_tweets)}/{self.max_tweets_per_session} tweets")
                self.logger.info(f"   Use resume in next session to continue from where we left off!")
                break
            
            
            is_at_bottom = await self.page.evaluate('''
                () => {
                    return window.innerHeight + window.scrollY >= document.body.scrollHeight - 100;
                }
            ''')
            

            if is_at_bottom and self.scroll_attempts_without_new > 10:
                self.logger.info("Reached bottom of timeline and no new tweets - stopping")
                break
            
            
            if scroll_attempts % 100 == 0:
                self.logger.info("Deep page refresh to trigger more tweet loading...")
                await self.page.evaluate('window.scrollTo(0, 0);')  
                await asyncio.sleep(self.timeouts['page_refresh_short_delay'])
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight);') 
                await asyncio.sleep(self.timeouts['page_refresh_long_delay'])
            
            
            if scroll_attempts % 50 == 0:
                elapsed = (time.time() - self.start_time) if self.start_time is not None else 0
                rate = len(self.all_tweets) / elapsed if elapsed > 0 else 0
                self.logger.info(f"Progress: {len(self.all_tweets)} tweets in {elapsed:.0f}s ({rate:.1f} tweets/s)")
                
            if self.start_time is not None:
                elapsed_time: float = time.time() - self.start_time
                if elapsed_time > 600 and len(self.all_tweets) == 0:
                    self.logger.error("Been scrolling for 10 minutes with 0 tweets - stopping to prevent crash")
                    self.logger.error("   This usually means tweet extraction is broken")
                    break
        
        self.logger.info(f"Scrolling completed after {scroll_attempts} attempts")
    
    def _save_final_tweets(self, username: str):    
        if not self.all_tweets:
            self.logger.warning("No tweets to save")
            return
        
        try:
            data_dir = Path(f"data/{username}")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            
            filename = data_dir / f"tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            output_data = {
                'username': username,
                'user_data': self.user_data,
                'tweet_count': len(self.all_tweets),
                'scraped_at': datetime.now().isoformat(),
                'scraping_duration_seconds': (time.time() - self.start_time) if self.start_time is not None else 0,
                'tweets': self.all_tweets
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Saved {len(self.all_tweets)} tweets to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving tweets: {e}")
    
    async def cleanup(self):
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("Playwright resources cleaned up")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")