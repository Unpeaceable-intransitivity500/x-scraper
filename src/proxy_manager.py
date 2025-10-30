import asyncio
import logging
import random
import time
from typing import Dict, List, Optional, Any
import aiohttp
import requests
from fake_useragent import UserAgent


class ProxyManager:
    
    def __init__(self, proxies: List[Dict[str, str]] = [], rotation_url: str = ""):
        self.logger = logging.getLogger(__name__)
        self.proxies = proxies or []
        self.rotation_url = rotation_url
        self.proxy_stats = {}
        self.current_proxy_index = 0
        self.failed_proxies = set()
        self.ua = UserAgent()
        
        if rotation_url:
            self.logger.info(f"Manual rotation API configured")
        
        for i in range(len(self.proxies)):
            self.proxy_stats[i] = {
                'success_count': 0,
                'failure_count': 0,
                'last_used': 0,
                'response_time': 0,
                'is_working': True
            }
    
    def add_proxy(self, proxy: Dict[str, str]) -> None:
        self.proxies.append(proxy)
        index = len(self.proxies) - 1
        self.proxy_stats[index] = {
            'success_count': 0,
            'failure_count': 0,
            'last_used': 0,
            'response_time': 0,
            'is_working': True
        }
        self.logger.info(f"Added proxy: {proxy.get('http', 'Unknown')}")
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        if not self.proxies:
            return None
        
        working_proxies = [
            i for i in range(len(self.proxies)) 
            if i not in self.failed_proxies and self.proxy_stats[i]['is_working']
        ]
        
        if not working_proxies:
            self.logger.warning("All proxies failed, resetting failure list")
            self.failed_proxies.clear()
            for i in self.proxy_stats:
                self.proxy_stats[i]['is_working'] = True
            working_proxies = list(range(len(self.proxies)))
        
        best_proxy_index = self._select_best_proxy(working_proxies)
        self.current_proxy_index = best_proxy_index
        
        return self.proxies[best_proxy_index]
    
    def _select_best_proxy(self, working_proxies: List[int]) -> int:
        if len(working_proxies) == 1:
            return working_proxies[0]
        
        proxy_scores = []
        current_time = time.time()
        
        for proxy_index in working_proxies:
            stats = self.proxy_stats[proxy_index]
            
            total_requests = stats['success_count'] + stats['failure_count']
            success_rate = stats['success_count'] / max(total_requests, 1)
            
            time_since_last_use = current_time - stats['last_used']
            recency_bonus = min(time_since_last_use / 300, 1.0) 
            
            response_time_penalty = min(stats['response_time'] / 10, 1.0)  
            
            score = (success_rate * 0.5) + (recency_bonus * 0.3) - (response_time_penalty * 0.2)
            proxy_scores.append((proxy_index, score))
        
        proxy_scores.sort(key=lambda x: x[1], reverse=True)
        
        top_performers = proxy_scores[:min(3, len(proxy_scores))]
        weights = [score for _, score in top_performers]
        
        if sum(weights) > 0:
            selected = random.choices(top_performers, weights=weights)[0]
            return selected[0]
        else:
            return random.choice(working_proxies)
    
    def mark_proxy_success(self, proxy_index: int, response_time: float) -> None:
        if proxy_index in self.proxy_stats:
            stats = self.proxy_stats[proxy_index]
            stats['success_count'] += 1
            stats['last_used'] = time.time()
            stats['response_time'] = response_time
            stats['is_working'] = True
            
            self.failed_proxies.discard(proxy_index)
    
    def mark_proxy_failure(self, proxy_index: int) -> None:
        if proxy_index in self.proxy_stats:
            stats = self.proxy_stats[proxy_index]
            stats['failure_count'] += 1
            
            total_requests = stats['success_count'] + stats['failure_count']
            failure_rate = stats['failure_count'] / max(total_requests, 1)
            
            if failure_rate > 0.7 or stats['failure_count'] >= 5:
                stats['is_working'] = False
                self.failed_proxies.add(proxy_index)
                self.logger.warning(f"Proxy {proxy_index} marked as not working (failure rate: {failure_rate:.2f})")
    
    async def validate_proxy(self, proxy: Dict[str, str]) -> bool:
        test_urls = [
            'http://httpbin.org/ip',
            'https://api.ipify.org?format=json',
            'http://ip-api.com/json'
        ]
        
        for url in test_urls:
            try:
                start_time = time.time()
                
                async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=False),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as session:
                    async with session.get(url, proxy=proxy.get('http')) as response:
                        if response.status == 200:
                            response_time = time.time() - start_time
                            self.logger.info(f"Proxy validation successful: {proxy.get('http')} ({response_time:.2f}s)")
                            return True
                            
            except Exception as e:
                self.logger.debug(f"Proxy validation failed for {url}: {str(e)}")
                continue
        
        return False
    
    async def validate_all_proxies(self) -> None:
        if not self.proxies:
            return
        
        self.logger.info(f"Validating {len(self.proxies)} proxies...")
        
        validation_tasks = []
        for i, proxy in enumerate(self.proxies):
            task = self._validate_single_proxy(i, proxy)
            validation_tasks.append(task)
        
        await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        working_count = sum(1 for stats in self.proxy_stats.values() if stats['is_working'])
        self.logger.info(f"Proxy validation complete: {working_count}/{len(self.proxies)} working")
    
    async def _validate_single_proxy(self, index: int, proxy: Dict[str, str]) -> None:
        try:
            is_working = await self.validate_proxy(proxy)
            self.proxy_stats[index]['is_working'] = is_working
            
            if not is_working:
                self.failed_proxies.add(index)
                
        except Exception as e:
            self.logger.error(f"Error validating proxy {index}: {str(e)}")
            self.proxy_stats[index]['is_working'] = False
            self.failed_proxies.add(index)
    
    def get_random_user_agent(self) -> str:
        try:
            return self.ua.chrome
        except Exception:
            fallback_agents = [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0"
            ]
            return random.choice(fallback_agents)
    
    def trigger_manual_rotation(self) -> bool:
        if not self.rotation_url:
            self.logger.debug("No rotation URL configured")
            return False
        
        try:
            self.logger.info("Triggering manual proxy rotation...")
            response = requests.get(self.rotation_url, timeout=10)
            response.raise_for_status()
            self.logger.info("Proxy IP rotated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to rotate proxy: {str(e)}")
            return False
    
    def get_proxy_stats(self) -> Dict[str, Any]:
        if not self.proxies:
            return {"total_proxies": 0, "working_proxies": 0, "failed_proxies": 0}
        
        working_proxies = sum(1 for stats in self.proxy_stats.values() if stats['is_working'])
        failed_proxies = len(self.failed_proxies)
        
        total_requests = sum(
            stats['success_count'] + stats['failure_count'] 
            for stats in self.proxy_stats.values()
        )
        
        total_successes = sum(stats['success_count'] for stats in self.proxy_stats.values())
        
        success_rate = (total_successes / max(total_requests, 1)) * 100
        
        return {
            "total_proxies": len(self.proxies),
            "working_proxies": working_proxies,
            "failed_proxies": failed_proxies,
            "total_requests": total_requests,
            "success_rate": round(success_rate, 2),
            "current_proxy_index": self.current_proxy_index,
            "proxy_details": [
                {
                    "index": i,
                    "proxy": proxy.get('http', 'Unknown'),
                    "is_working": self.proxy_stats[i]['is_working'],
                    "success_count": self.proxy_stats[i]['success_count'],
                    "failure_count": self.proxy_stats[i]['failure_count'],
                    "response_time": self.proxy_stats[i]['response_time']
                }
                for i, proxy in enumerate(self.proxies)
            ]
        }
    
    @staticmethod
    def load_proxies_from_list(proxy_list: List[str]) -> List[Dict[str, str]]:
        
        proxies = []
        
        for proxy_str in proxy_list:
            try:
                if '://' in proxy_str:
                   
                    proxies.append({
                        'http': proxy_str,
                        'https': proxy_str
                    })
                elif proxy_str.count(':') == 1:
                   
                    ip, port = proxy_str.split(':')
                    proxy_url = f"http://{ip}:{port}"
                    proxies.append({
                        'http': proxy_url,
                        'https': proxy_url
                    })
                elif proxy_str.count(':') == 3:
                    
                    ip, port, user, password = proxy_str.split(':')

                    if port == '20000':
                        proxy_url = f"http://{user}:{password}@{ip}:{port}"
                        proxies.append({
                            'http': proxy_url,
                            'https': proxy_url,
                            'type': 'http'
                        })
                    elif port == '20002':
                        
                        proxy_url = f"socks5://{user}:{password}@{ip}:{port}"
                        proxies.append({
                            'http': proxy_url,
                            'https': proxy_url,
                            'type': 'socks5'
                        })
                    else:
                        
                        proxy_url = f"http://{user}:{password}@{ip}:{port}"
                        proxies.append({
                            'http': proxy_url,
                            'https': proxy_url,
                            'type': 'http'
                        })
                else:
                    logging.warning(f"Unsupported proxy format: {proxy_str}")
                    
            except Exception as e:
                logging.error(f"Error parsing proxy {proxy_str}: {str(e)}")
                
        return proxies
