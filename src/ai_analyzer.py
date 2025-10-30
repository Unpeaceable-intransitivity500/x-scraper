import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from enum import Enum
import json

from .prompts import AnalysisPrompts

try:
    import openai  # type: ignore
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None  
    OPENAI_AVAILABLE = False


class AIProvider(Enum):
    OPENAI = "openai"


class AnalysisType(Enum):
    SENTIMENT = "sentiment"
    TOPICS = "topics"
    SUMMARY = "summary"
    CLASSIFICATION = "classification"
    ENTITIES = "entities"
    TRENDS = "trends"
    ENGAGEMENT = "engagement"
    CUSTOM = "custom"


class AIAnalyzer:
    
    def __init__(self, api_key: str = "", model: str = "gpt-4", 
                 max_tokens: int = 1000, temperature: float = 0.7):
        self.provider = AIProvider.OPENAI
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        self.logger = logging.getLogger(__name__)
        self.client = None
        
        self._initialize_client()

        self.analysis_cache = {}
        self.cache_ttl = 3600
        
        self.batch_sizes = {
            AnalysisType.SENTIMENT: 25,    
            AnalysisType.TOPICS: 15,       
            AnalysisType.SUMMARY: 20,      
            AnalysisType.CLASSIFICATION: 30, 
            AnalysisType.ENTITIES: 25,     
            AnalysisType.TRENDS: 10,       
            AnalysisType.ENGAGEMENT: 20,   
            AnalysisType.CUSTOM: 15        
        }
    
    def _initialize_client(self) -> None:
        try:
            if not OPENAI_AVAILABLE or not openai:
                raise ImportError("OpenAI library not installed")
            if not self.api_key:
                raise ValueError("OpenAI API key not provided")
            
            self.client = openai.AsyncOpenAI(api_key=self.api_key)  # type: ignore
            self.logger.info("OpenAI client initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize AI client: {str(e)}")
            self.client = None
    
    def _extract_essential_tweet_data(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        essential_data = {
            'texts': [],
            'engagement_metrics': [],
            'metadata': []
        }
        
        for tweet in tweets:
            text = tweet.get('text', '').strip()
            if text:
                essential_data['texts'].append(text)
                
                metrics = tweet.get('metrics', {})
                essential_data['engagement_metrics'].append({
                    'retweet_count': metrics.get('retweet_count', 0),
                    'favorite_count': metrics.get('favorite_count', 0),
                    'reply_count': metrics.get('reply_count', 0),
                    'quote_count': metrics.get('quote_count', 0),
                    'view_count': str(metrics.get('view_count', '0')).replace(',', '') if metrics.get('view_count') else '0'
                })
                
                essential_data['metadata'].append({
                    'created_at': tweet.get('created_at', ''),
                    'lang': tweet.get('lang', 'en'),
                    'has_media': len(tweet.get('media', [])) > 0,
                    'has_hashtags': len(tweet.get('hashtags', [])) > 0,
                    'hashtags': tweet.get('hashtags', []),
                    'is_reply': tweet.get('is_reply', False),
                    'is_retweet': tweet.get('is_retweet', False),
                    'text_length': len(text)
                })
        
        return essential_data

    def _create_batches(self, data: List[Any], batch_size: int) -> List[List[Any]]:
        batches = []
        for i in range(0, len(data), batch_size):
            batches.append(data[i:i + batch_size])
        return batches

    async def _process_batches(self, analysis_type: AnalysisType, batches: List[Any], 
                             process_func, combine_func) -> Dict[str, Any]:
        self.logger.info(f"Processing {len(batches)} batches for {analysis_type.value} analysis")
        
        max_concurrent_batches = min(5, len(batches)) 
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_single_batch(i: int, batch: Any) -> Dict[str, Any]:
            async with semaphore:
                self.logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} items)")
                try:
                    if i > 0:
                        await asyncio.sleep(0.5)
                    result = await process_func(batch)
                    return result
                except Exception as e:
                    self.logger.error(f"Batch {i+1} failed: {str(e)}")
                    return {"error": f"Batch {i+1} failed: {str(e)}"}
        
        start_time = time.time()
        batch_tasks = [process_single_batch(i, batch) for i, batch in enumerate(batches)]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch {i+1} failed with exception: {str(result)}")
                processed_results.append({"error": f"Batch {i+1} failed: {str(result)}"})
            else:
                processed_results.append(result)
        
        parallel_time = time.time() - start_time
        self.logger.info(f"Parallel batch processing completed in {parallel_time:.2f}s")
        
        return combine_func(processed_results)

    def _calculate_token_savings(self, original_tweets: List[Dict[str, Any]], 
                               essential_data: Dict[str, Any]) -> int:
        try:
            original_size = len(json.dumps(original_tweets, default=str))
            essential_size = len(json.dumps(essential_data, default=str))
            savings = ((original_size - essential_size) / original_size) * 100
            return int(savings)
        except:
            return 0

    async def analyze_tweets(self, tweets: List[Dict[str, Any]], 
                           analysis_types: List[AnalysisType],
                           custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("AI client not initialized")
        
        if not tweets:
            return {"error": "No tweets provided for analysis"}
        
        self.logger.info(f"Analyzing {len(tweets)} tweets with {len(analysis_types)} analysis types")
        
        essential_data = self._extract_essential_tweet_data(tweets)
        token_savings = self._calculate_token_savings(tweets, essential_data)
        self.logger.info(f"Token optimization: ~{token_savings}% reduction in data size")
        
        results = {
            "tweet_count": len(tweets),
            "analysis_timestamp": time.time(),
            "analyses": {}
        }
        
        tweet_texts = essential_data['texts']
        
        analysis_tasks = []
        
        for analysis_type in analysis_types:
            batch_size = self.batch_sizes.get(analysis_type, 20)
            needs_batching = len(tweet_texts) > batch_size
            
            if needs_batching:
                self.logger.info(f"Large dataset detected ({len(tweet_texts)} tweets), using batch processing for {analysis_type.value}")
            
            if analysis_type == AnalysisType.SENTIMENT:
                task = self._analyze_sentiment_batched(tweet_texts) if needs_batching else self._analyze_sentiment(tweet_texts)
            elif analysis_type == AnalysisType.TOPICS:
                task = self._analyze_topics_batched(tweet_texts) if needs_batching else self._analyze_topics(tweet_texts)
            elif analysis_type == AnalysisType.SUMMARY:
                task = self._generate_summary_batched(tweet_texts) if needs_batching else self._generate_summary(tweet_texts)
            elif analysis_type == AnalysisType.CLASSIFICATION:
                task = self._classify_tweets_batched(tweet_texts) if needs_batching else self._classify_tweets(tweet_texts)
            elif analysis_type == AnalysisType.ENTITIES:
                task = self._extract_entities_batched(tweet_texts) if needs_batching else self._extract_entities(tweet_texts)
            elif analysis_type == AnalysisType.TRENDS:
                task = self._analyze_trends_batched(essential_data) if needs_batching else self._analyze_trends(essential_data)
            elif analysis_type == AnalysisType.ENGAGEMENT:
                task = self._analyze_engagement_batched(essential_data) if needs_batching else self._analyze_engagement(essential_data)
            elif analysis_type == AnalysisType.CUSTOM and custom_prompt:
                task = self._custom_analysis_batched(tweet_texts, custom_prompt) if needs_batching else self._custom_analysis(tweet_texts, custom_prompt)
            else:
                continue
            
            analysis_tasks.append((analysis_type, task))
        
        if analysis_tasks:
            self.logger.info(f"Running {len(analysis_tasks)} analysis types in parallel")
            start_time = time.time()
            
            tasks = [task for _, task in analysis_tasks]
            try:
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, (analysis_type, _) in enumerate(analysis_tasks):
                    result = task_results[i]
                    if isinstance(result, Exception):
                        self.logger.error(f"Analysis failed for {analysis_type.value}: {str(result)}")
                        results["analyses"][analysis_type.value] = {"error": str(result)}
                    else:
                        results["analyses"][analysis_type.value] = result
                
                parallel_time = time.time() - start_time
                self.logger.info(f"Parallel analysis completed in {parallel_time:.2f}s (vs {len(analysis_tasks) * 15:.1f}s sequential estimated)")
                
            except Exception as e:
                self.logger.error(f"Parallel analysis failed: {str(e)}")

                for analysis_type, task in analysis_tasks:
                    try:
                        results["analyses"][analysis_type.value] = await task
                    except Exception as task_error:
                        self.logger.error(f"Analysis failed for {analysis_type.value}: {str(task_error)}")
                        results["analyses"][analysis_type.value] = {"error": str(task_error)}
        
        return results
    
    async def _analyze_sentiment(self, tweet_texts: List[str]) -> Dict[str, Any]:
        cache_key = f"sentiment_{hash(str(tweet_texts))}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        prompt = AnalysisPrompts.sentiment_analysis(tweet_texts)
        
        result = await self._make_ai_request(prompt)
        self._cache_result(cache_key, result)
        return result
    
    async def _analyze_topics(self, tweet_texts: List[str]) -> Dict[str, Any]:
        cache_key = f"topics_{hash(str(tweet_texts))}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        prompt = AnalysisPrompts.topic_analysis(tweet_texts)
        
        result = await self._make_ai_request(prompt)
        self._cache_result(cache_key, result)
        return result
    
    async def _generate_summary(self, tweet_texts: List[str]) -> Dict[str, Any]:
        cache_key = f"summary_{hash(str(tweet_texts))}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        prompt = AnalysisPrompts.summary_generation(tweet_texts)
        
        result = await self._make_ai_request(prompt)
        self._cache_result(cache_key, result)
        return result
    
    async def _classify_tweets(self, tweet_texts: List[str]) -> Dict[str, Any]:
        cache_key = f"classification_{hash(str(tweet_texts))}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        prompt = AnalysisPrompts.classification_analysis(tweet_texts)
        
        result = await self._make_ai_request(prompt)
        self._cache_result(cache_key, result)
        return result
    
    async def _extract_entities(self, tweet_texts: List[str]) -> Dict[str, Any]:
        cache_key = f"entities_{hash(str(tweet_texts))}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        prompt = AnalysisPrompts.entity_extraction(tweet_texts)
        
        result = await self._make_ai_request(prompt)
        self._cache_result(cache_key, result)
        return result
    
    async def _analyze_trends(self, essential_data: Dict[str, Any]) -> Dict[str, Any]:
        tweet_data = []
        texts = essential_data['texts'][:100]
        metrics = essential_data['engagement_metrics'][:100]
        metadata = essential_data['metadata'][:100]
        
        for i, text in enumerate(texts):
            if i < len(metrics) and i < len(metadata):
                tweet_data.append({
                    'text': text,
                    'created_at': metadata[i].get('created_at', ''),
                    'retweet_count': metrics[i].get('retweet_count', 0),
                    'favorite_count': metrics[i].get('favorite_count', 0),
                    'reply_count': metrics[i].get('reply_count', 0),
                    'hashtags': metadata[i].get('hashtags', [])
                })
        
        prompt = AnalysisPrompts.trend_analysis(tweet_data)
        
        return await self._make_ai_request(prompt)
    
    async def _analyze_engagement(self, essential_data: Dict[str, Any]) -> Dict[str, Any]:
        engagement_data = []
        texts = essential_data['texts'][:100]
        metrics = essential_data['engagement_metrics'][:100]
        metadata = essential_data['metadata'][:100]
        
        for i, text in enumerate(texts):
            if i < len(metrics) and i < len(metadata):
                engagement_data.append({
                    'text_length': metadata[i].get('text_length', len(text)),
                    'retweet_count': metrics[i].get('retweet_count', 0),
                    'favorite_count': metrics[i].get('favorite_count', 0),
                    'reply_count': metrics[i].get('reply_count', 0),
                    'quote_count': metrics[i].get('quote_count', 0),
                    'view_count': metrics[i].get('view_count', '0'),
                    'has_media': metadata[i].get('has_media', False),
                    'has_hashtags': metadata[i].get('has_hashtags', False),
                    'is_reply': metadata[i].get('is_reply', False),
                    'is_retweet': metadata[i].get('is_retweet', False),
                    'lang': metadata[i].get('lang', 'en')
                })
        
        prompt = AnalysisPrompts.engagement_analysis(engagement_data)
        
        return await self._make_ai_request(prompt)
    
    async def _custom_analysis(self, tweet_texts: List[str], custom_prompt: str) -> Dict[str, Any]:
        prompt = AnalysisPrompts.custom_analysis(tweet_texts, custom_prompt)
        
        return await self._make_ai_request(prompt)
    
    async def _analyze_topics_batched(self, tweet_texts: List[str]) -> Dict[str, Any]:
        batch_size = self.batch_sizes[AnalysisType.TOPICS]
        batches = self._create_batches(tweet_texts, batch_size)
        
        async def process_batch(batch):
            return await self._analyze_topics(batch)
        
        def combine_results(batch_results):
            all_topics = {}
            all_hashtags = []
            
            for result in batch_results:
                if "error" not in result:
                    top_topics = result.get("top_topics", [])
                    for topic in top_topics:
                        topic_name = topic.get("topic", "")
                        if topic_name in all_topics:
                            all_topics[topic_name]["frequency"] += topic.get("frequency", 0)
                            all_topics[topic_name]["keywords"].extend(topic.get("keywords", []))
                        else:
                            all_topics[topic_name] = {
                                "frequency": topic.get("frequency", 0),
                                "keywords": topic.get("keywords", []),
                                "category": topic.get("category", "General")
                            }
                    
                    hashtag_analysis = result.get("hashtag_analysis", {})
                    trending_hashtags = hashtag_analysis.get("trending_hashtags", [])
                    all_hashtags.extend(trending_hashtags)
            
            sorted_topics = sorted(all_topics.items(), key=lambda x: x[1]["frequency"], reverse=True)[:10]
            top_topics = []
            for topic_name, topic_data in sorted_topics:
                unique_keywords = list(set(topic_data["keywords"]))[:5]
                top_topics.append({
                    "topic": topic_name,
                    "frequency": round(topic_data["frequency"] / len(batch_results), 2),
                    "keywords": unique_keywords,
                    "category": topic_data["category"]
                })
            
            hashtag_counts = {}
            for hashtag in all_hashtags:
                hashtag_counts[hashtag] = hashtag_counts.get(hashtag, 0) + 1
            
            trending_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "top_topics": top_topics,
                "hashtag_analysis": {
                    "trending_hashtags": [ht[0] for ht in trending_hashtags]
                },
                "batches_processed": len(batch_results),
                "insights": f"Analyzed topics across {len(batch_results)} batches covering {len(tweet_texts)} tweets, found {len(all_topics)} unique topics"
            }
        
        return await self._process_batches(AnalysisType.TOPICS, batches, process_batch, combine_results)

    async def _analyze_sentiment_batched(self, tweet_texts: List[str]) -> Dict[str, Any]:
        batch_size = self.batch_sizes[AnalysisType.SENTIMENT]
        batches = self._create_batches(tweet_texts, batch_size)
        
        async def process_batch(batch):
            return await self._analyze_sentiment(batch)
        
        def combine_results(batch_results):
            all_individual_sentiments = []
            positive_total = negative_total = neutral_total = 0
            total_tweets = 0
            
            for result in batch_results:
                if "error" not in result:
                    individual = result.get("individual_sentiments", [])
                    for sentiment in individual:
                        sentiment["tweet_index"] = sentiment["tweet_index"] + total_tweets
                    all_individual_sentiments.extend(individual)
                    
                    overall = result.get("overall_sentiment", {})
                    batch_size = len(individual)
                    positive_total += (overall.get("positive", 0) * batch_size / 100)
                    negative_total += (overall.get("negative", 0) * batch_size / 100)
                    neutral_total += (overall.get("neutral", 0) * batch_size / 100)
                    total_tweets += batch_size
            
            if total_tweets > 0:
                overall_sentiment = {
                    "positive": round((positive_total / total_tweets) * 100),
                    "negative": round((negative_total / total_tweets) * 100),
                    "neutral": round((neutral_total / total_tweets) * 100)
                }
            else:
                overall_sentiment = {"positive": 0, "negative": 0, "neutral": 100}
            
            return {
                "overall_sentiment": overall_sentiment,
                "individual_sentiments": all_individual_sentiments[:50], 
                "batches_processed": len(batch_results),
                "insights": f"Analyzed {total_tweets} tweets across {len(batch_results)} batches"
            }
        
        return await self._process_batches(AnalysisType.SENTIMENT, batches, process_batch, combine_results)

    async def _generate_summary_batched(self, tweet_texts: List[str]) -> Dict[str, Any]:
        batch_size = self.batch_sizes[AnalysisType.SUMMARY]
        batches = self._create_batches(tweet_texts, batch_size)
        
        async def process_batch(batch):
            return await self._generate_summary(batch)
        
        def combine_results(batch_results):
            all_summaries = []
            all_themes = []
            
            for result in batch_results:
                if "error" not in result:
                    summary = result.get("summary", "")
                    if summary:
                        all_summaries.append(summary)
                    themes = result.get("key_themes", [])
                    all_themes.extend(themes)
            
            combined_summary = " ".join(all_summaries)
            unique_themes = list(set(all_themes))[:10]
            
            return {
                "summary": f"Analysis of {len(tweet_texts)} tweets: {combined_summary}",
                "key_themes": unique_themes,
                "batches_processed": len(batch_results)
            }
        
        return await self._process_batches(AnalysisType.SUMMARY, batches, process_batch, combine_results)

    async def _classify_tweets_batched(self, tweet_texts: List[str]) -> Dict[str, Any]:
        batch_size = self.batch_sizes[AnalysisType.CLASSIFICATION]
        batches = self._create_batches(tweet_texts, batch_size)
        
        async def process_batch(batch):
            return await self._classify_tweets(batch)
        
        def combine_results(batch_results):
            all_classifications = {}
            total_tweets = 0
            
            for result in batch_results:
                if "error" not in result:
                    categories = result.get("categories", {})
                    for category, count in categories.items():
                        all_classifications[category] = all_classifications.get(category, 0) + count
                        total_tweets += count
            
            if total_tweets > 0:
                category_percentages = {cat: round((count/total_tweets)*100, 1) 
                                     for cat, count in all_classifications.items()}
            else:
                category_percentages = {}
            
            return {
                "categories": category_percentages,
                "total_tweets": total_tweets,
                "batches_processed": len(batch_results)
            }
        
        return await self._process_batches(AnalysisType.CLASSIFICATION, batches, process_batch, combine_results)

    async def _extract_entities_batched(self, tweet_texts: List[str]) -> Dict[str, Any]:
        batch_size = self.batch_sizes[AnalysisType.ENTITIES]
        batches = self._create_batches(tweet_texts, batch_size)
        
        async def process_batch(batch):
            return await self._extract_entities(batch)
        
        def combine_results(batch_results):
            all_entities = {"people": [], "organizations": [], "locations": [], "other": []}
            
            for result in batch_results:
                if "error" not in result:
                    entities = result.get("entities", {})
                    for entity_type, entity_list in entities.items():
                        if entity_type in all_entities:
                            all_entities[entity_type].extend(entity_list)
            
            for entity_type in all_entities:
                entity_counts = {}
                for entity in all_entities[entity_type]:
                    entity_counts[entity] = entity_counts.get(entity, 0) + 1
                
                sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:20]
                all_entities[entity_type] = [entity[0] for entity in sorted_entities]
            
            return {
                "entities": all_entities,
                "batches_processed": len(batch_results)
            }
        
        return await self._process_batches(AnalysisType.ENTITIES, batches, process_batch, combine_results)

    async def _analyze_trends_batched(self, essential_data: Dict[str, Any]) -> Dict[str, Any]:
        batch_size = self.batch_sizes[AnalysisType.TRENDS]
        texts = essential_data['texts']
        metrics = essential_data['engagement_metrics']
        metadata = essential_data['metadata']
        
        batches = []
        for i in range(0, len(texts), batch_size):
            batch_data = {
                'texts': texts[i:i + batch_size],
                'engagement_metrics': metrics[i:i + batch_size],
                'metadata': metadata[i:i + batch_size]
            }
            batches.append(batch_data)
        
        async def process_batch(batch_data):
            return await self._analyze_trends(batch_data)
        
        def combine_results(batch_results):
            return {
                "trends": f"Combined trend analysis from {len(batch_results)} batches covering {len(texts)} tweets",
                "batches_processed": len(batch_results),
                "insights": f"Processed {len(texts)} tweets in {len(batch_results)} batches for trend analysis"
            }
        
        return await self._process_batches(AnalysisType.TRENDS, batches, process_batch, combine_results)

    async def _analyze_engagement_batched(self, essential_data: Dict[str, Any]) -> Dict[str, Any]:
        batch_size = self.batch_sizes[AnalysisType.ENGAGEMENT]
        texts = essential_data['texts']
        metrics = essential_data['engagement_metrics']
        metadata = essential_data['metadata']
        
        batches = []
        for i in range(0, len(texts), batch_size):
            batch_data = {
                'texts': texts[i:i + batch_size],
                'engagement_metrics': metrics[i:i + batch_size],
                'metadata': metadata[i:i + batch_size]
            }
            batches.append(batch_data)
        
        async def process_batch(batch_data):
            return await self._analyze_engagement(batch_data)
        
        def combine_results(batch_results):
            return {
                "engagement": f"Combined engagement analysis from {len(batch_results)} batches covering {len(texts)} tweets",
                "batches_processed": len(batch_results),
                "insights": f"Processed {len(texts)} tweets in {len(batch_results)} batches for engagement analysis"
            }
        
        return await self._process_batches(AnalysisType.ENGAGEMENT, batches, process_batch, combine_results)

    async def _custom_analysis_batched(self, tweet_texts: List[str], custom_prompt: str) -> Dict[str, Any]:

        batch_size = self.batch_sizes[AnalysisType.CUSTOM]
        batches = self._create_batches(tweet_texts, batch_size)
        
        async def process_batch(batch):
            return await self._custom_analysis(batch, custom_prompt)
        
        def combine_results(batch_results):
            all_results = []
            for result in batch_results:
                if "error" not in result:
                    all_results.append(result.get("analysis", ""))
            
            return {
                "analysis": " ".join(all_results),
                "batches_processed": len(batch_results),
                "custom_prompt": custom_prompt
            }
        
        return await self._process_batches(AnalysisType.CUSTOM, batches, process_batch, combine_results)
    
    async def _make_ai_request(self, prompt: str) -> Dict[str, Any]:
        try:
            return await self._make_openai_request(prompt)
                
        except Exception as e:
            self.logger.error(f"AI request failed: {str(e)}")
            return {"error": str(e)}
    
    async def _make_openai_request(self, prompt: str) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
            
        try:
            response = await self.client.chat.completions.create(  
                model=self.model,
                messages=[
                    {"role": "system", "content": AnalysisPrompts.get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"analysis": content, "format": "text"}
                
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        if cache_key in self.analysis_cache:
            cached_data = self.analysis_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                self.logger.info(f"Using cached result for {cache_key}")
                return cached_data['result']
            else:
                del self.analysis_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        self.analysis_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
    
    def clear_cache(self) -> None:
        self.analysis_cache.clear()
        self.logger.info("Analysis cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        current_time = time.time()
        valid_entries = sum(
            1 for entry in self.analysis_cache.values()
            if current_time - entry['timestamp'] < self.cache_ttl
        )
        
        return {
            'total_entries': len(self.analysis_cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self.analysis_cache) - valid_entries,
            'cache_ttl': self.cache_ttl
        }