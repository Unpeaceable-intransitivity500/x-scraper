from typing import List, Dict, Any
import json


class AnalysisPrompts:
    
    @staticmethod
    def sentiment_analysis(tweet_texts: List[str]) -> str:
        return f"""
        Analyze the sentiment of the following {len(tweet_texts)} tweets. 
        Provide:
        1. Overall sentiment distribution (positive, negative, neutral percentages)
        2. Individual tweet sentiments with confidence scores
        3. Key emotional themes and patterns
        4. Sentiment trends if applicable
        5. Notable emotional indicators (words, phrases, emojis)
        
        Tweets:
        {chr(10).join([f"{i+1}. {text}" for i, text in enumerate(tweet_texts[:50])])}
        
        Respond in JSON format with the following structure:
        {{
            "overall_sentiment": {{
                "positive": percentage,
                "negative": percentage,
                "neutral": percentage
            }},
            "individual_sentiments": [
                {{"tweet_index": 1, "sentiment": "positive/negative/neutral", "confidence": 0.85, "reasoning": "explanation"}}
            ],
            "emotional_themes": ["theme1", "theme2"],
            "key_indicators": {{
                "positive_words": ["word1", "word2"],
                "negative_words": ["word1", "word2"],
                "neutral_indicators": ["word1", "word2"]
            }},
            "insights": "Overall sentiment analysis insights"
        }}
        """
    
    @staticmethod
    def topic_analysis(tweet_texts: List[str]) -> str:
        return f"""
        Analyze the topics and themes in the following {len(tweet_texts)} tweets.
        Provide:
        1. Top 10 most discussed topics with frequency scores
        2. Topic categories and subcategories
        3. Emerging themes and trending topics
        4. Topic clusters and relationships
        5. Hashtag analysis and keyword extraction
        
        Tweets:
        {chr(10).join([f"{i+1}. {text}" for i, text in enumerate(tweet_texts[:50])])}
        
        Respond in JSON format with structured topic data:
        {{
            "top_topics": [
                {{"topic": "topic_name", "frequency": 0.25, "keywords": ["key1", "key2"], "category": "category_name"}}
            ],
            "topic_categories": {{
                "technology": ["AI", "blockchain"],
                "politics": ["election", "policy"]
            }},
            "emerging_themes": ["theme1", "theme2"],
            "topic_relationships": [
                {{"topic1": "AI", "topic2": "technology", "relationship": "parent-child", "strength": 0.8}}
            ],
            "hashtag_analysis": {{
                "trending_hashtags": ["#hashtag1", "#hashtag2"],
                "hashtag_topics": {{"#AI": "technology", "#election": "politics"}}
            }},
            "insights": "Key insights about topic distribution and trends"
        }}
        """
    
    @staticmethod
    def summary_generation(tweet_texts: List[str]) -> str:
        return f"""
        Create a comprehensive summary of the following {len(tweet_texts)} tweets.
        Include:
        1. Main themes and topics discussed
        2. Key insights and takeaways
        3. Notable quotes or statements (with attribution)
        4. Overall narrative or story arc
        5. Actionable insights and recommendations
        6. Timeline of events if applicable
        
        Tweets:
        {chr(10).join([f"{i+1}. {text}" for i, text in enumerate(tweet_texts[:50])])}
        
        Provide a well-structured summary in JSON format:
        {{
            "executive_summary": "Brief overview of the main points",
            "main_themes": ["theme1", "theme2", "theme3"],
            "key_insights": [
                {{"insight": "insight description", "supporting_evidence": "evidence from tweets", "importance": "high/medium/low"}}
            ],
            "notable_quotes": [
                {{"quote": "exact quote", "author": "username or description", "context": "why this quote is significant"}}
            ],
            "narrative": "The overall story or progression of events",
            "actionable_insights": [
                {{"recommendation": "what to do", "rationale": "why this matters", "priority": "high/medium/low"}}
            ],
            "timeline": [
                {{"event": "event description", "timeframe": "when it happened", "significance": "why it matters"}}
            ],
            "conclusion": "Final thoughts and implications"
        }}
        """
    
    @staticmethod
    def classification_analysis(tweet_texts: List[str]) -> str:
        return f"""
        Classify the following {len(tweet_texts)} tweets into relevant categories.
        
        Primary categories include:
        - News/Information: Breaking news, factual updates, informational content
        - Opinion/Commentary: Personal views, analysis, editorial content
        - Personal/Lifestyle: Personal updates, daily life, experiences
        - Business/Marketing: Promotional content, business updates, advertisements
        - Entertainment: Humor, memes, celebrity content, pop culture
        - Technology: Tech news, product launches, technical discussions
        - Politics: Political news, policy discussions, political opinions
        - Sports: Sports news, game updates, athlete content
        - Education: Educational content, learning resources, academic discussions
        - Health: Health tips, medical news, wellness content
        - Social Issues: Activism, social causes, community issues
        
        Provide:
        1. Category distribution with percentages
        2. Individual tweet classifications with confidence scores
        3. Subcategory analysis where applicable
        4. Content quality assessment
        5. Engagement potential by category
        
        Tweets:
        {chr(10).join([f"{i+1}. {text}" for i, text in enumerate(tweet_texts[:50])])}
        
        Respond in JSON format:
        {{
            "category_distribution": {{
                "News/Information": 0.25,
                "Opinion/Commentary": 0.20
            }},
            "individual_classifications": [
                {{
                    "tweet_index": 1,
                    "primary_category": "Technology",
                    "subcategory": "AI/Machine Learning",
                    "confidence": 0.92,
                    "reasoning": "Discusses AI developments",
                    "secondary_categories": ["News/Information"]
                }}
            ],
            "content_quality": {{
                "high_quality": 0.30,
                "medium_quality": 0.50,
                "low_quality": 0.20
            }},
            "engagement_potential": {{
                "Technology": "high",
                "Personal/Lifestyle": "medium"
            }},
            "insights": "Key patterns in content categorization"
        }}
        """
    
    @staticmethod
    def entity_extraction(tweet_texts: List[str]) -> str:
        return f"""
        Extract and analyze named entities from the following {len(tweet_texts)} tweets.
        
        Entity types to identify:
        1. People: Names, usernames, public figures, influencers
        2. Organizations: Companies, institutions, government bodies
        3. Locations: Cities, countries, places, venues
        4. Products/Services: Brand names, product mentions, services
        5. Events: Conferences, meetings, launches, incidents
        6. Hashtags and mentions: Social media specific entities
        7. Dates/Times: Temporal references
        8. Money/Numbers: Financial figures, statistics
        
        Provide:
        - Entity frequency counts and importance scores
        - Entity types and detailed categories
        - Relationship networks between entities
        - Most influential entities and their impact
        - Sentiment associated with each entity
        
        Tweets:
        {chr(10).join([f"{i+1}. {text}" for i, text in enumerate(tweet_texts[:50])])}
        
        Respond in JSON format with structured entity data:
        {{
            "entities_by_type": {{
                "people": [
                    {{"name": "Elon Musk", "frequency": 5, "sentiment": "neutral", "influence_score": 0.9, "context": "CEO mentions"}}
                ],
                "organizations": [
                    {{"name": "Tesla", "frequency": 3, "sentiment": "positive", "type": "company", "industry": "automotive"}}
                ],
                "locations": [
                    {{"name": "San Francisco", "frequency": 2, "context": "event location", "country": "USA"}}
                ]
            }},
            "entity_relationships": [
                {{"entity1": "Elon Musk", "entity2": "Tesla", "relationship": "CEO_of", "strength": 0.95}}
            ],
            "most_influential": [
                {{"entity": "Elon Musk", "type": "person", "influence_score": 0.9, "reason": "High mention frequency and engagement"}}
            ],
            "hashtag_analysis": {{
                "trending": ["#AI", "#Tesla"],
                "entity_hashtags": {{"Tesla": ["#TSLA", "#ElectricVehicles"]}}
            }},
            "temporal_entities": [
                {{"entity": "Q4 2024", "type": "date", "context": "earnings report", "frequency": 2}}
            ],
            "insights": "Key patterns in entity mentions and relationships"
        }}
        """
    
    @staticmethod
    def trend_analysis(tweet_data: List[Dict[str, Any]]) -> str:
        return f"""
        Analyze trends in the following tweet data:
        {json.dumps(tweet_data, indent=2)}
        
        Identify and analyze:
        1. Temporal patterns: Posting times, frequency distributions, peak activity periods
        2. Engagement trends: Likes, retweets, replies patterns and correlations
        3. Content trends: Hashtags, topics, themes over time
        4. Viral content patterns: What makes content go viral
        5. Emerging vs declining trends: Rising and falling topics
        6. User behavior patterns: Posting habits, engagement styles
        7. Content performance metrics: Success factors and predictors
        
        Provide insights in JSON format:
        {{
            "temporal_patterns": {{
                "peak_hours": ["14:00-16:00", "20:00-22:00"],
                "peak_days": ["Tuesday", "Wednesday"],
                "posting_frequency": {{"average_per_hour": 12.5, "trend": "increasing"}}
            }},
            "engagement_trends": {{
                "average_likes": 150,
                "average_retweets": 25,
                "engagement_rate": 0.08,
                "high_performing_content": ["videos", "questions", "controversial topics"]
            }},
            "content_trends": {{
                "trending_hashtags": ["#trending1", "#trending2"],
                "declining_hashtags": ["#declining1"],
                "emerging_topics": ["topic1", "topic2"],
                "topic_lifecycle": {{"AI": "mature", "Web3": "declining", "Climate": "emerging"}}
            }},
            "viral_patterns": {{
                "viral_threshold": {{"likes": 1000, "retweets": 100}},
                "viral_factors": ["timing", "controversy", "humor", "breaking_news"],
                "viral_content_types": ["memes", "breaking_news", "celebrity_mentions"]
            }},
            "user_behavior": {{
                "active_users": 150,
                "engagement_distribution": {{"high": 0.2, "medium": 0.5, "low": 0.3}},
                "behavior_patterns": ["morning_news_sharing", "evening_entertainment"]
            }},
            "predictions": {{
                "trending_up": ["topic1", "hashtag1"],
                "trending_down": ["topic2", "hashtag2"],
                "next_viral_candidates": ["content_type1", "content_type2"]
            }},
            "insights": "Key insights about trending patterns and future predictions"
        }}
        """
    
    @staticmethod
    def engagement_analysis(engagement_data: List[Dict[str, Any]]) -> str:
        return f"""
        Analyze engagement patterns in the following tweet data:
        {json.dumps(engagement_data, indent=2)}
        
        Provide comprehensive insights on:
        1. Factors that drive high engagement (likes, retweets, replies)
        2. Optimal content characteristics for maximum reach
        3. Engagement rate distributions and benchmarks
        4. Correlation between content features and engagement
        5. Recommendations for improving engagement
        6. Audience behavior patterns
        7. Content optimization strategies
        
        Respond in JSON format with actionable insights:
        {{
            "engagement_drivers": {{
                "high_impact_factors": [
                    {{"factor": "text_length", "optimal_range": "100-150 characters", "impact_score": 0.8}},
                    {{"factor": "hashtags", "optimal_count": "2-3", "impact_score": 0.7}},
                    {{"factor": "media_presence", "impact": "increases_engagement_by_40%", "impact_score": 0.9}}
                ],
                "content_types": {{
                    "questions": {{"avg_engagement": 0.12, "best_practice": "end with question mark"}},
                    "images": {{"avg_engagement": 0.15, "best_practice": "high quality, relevant"}},
                    "videos": {{"avg_engagement": 0.20, "best_practice": "under 60 seconds"}}
                }}
            }},
            "optimal_characteristics": {{
                "text_length": {{"min": 80, "max": 150, "reasoning": "balance between information and readability"}},
                "posting_time": {{"optimal_hours": ["9-11", "14-16", "19-21"], "timezone": "user_local"}},
                "hashtag_strategy": {{"count": "2-3", "types": ["trending", "niche", "branded"]}},
                "media_recommendations": ["high_quality_images", "short_videos", "infographics"]
            }},
            "engagement_benchmarks": {{
                "excellent": {{"like_rate": "> 5%", "retweet_rate": "> 1%", "reply_rate": "> 0.5%"}},
                "good": {{"like_rate": "2-5%", "retweet_rate": "0.5-1%", "reply_rate": "0.2-0.5%"}},
                "average": {{"like_rate": "1-2%", "retweet_rate": "0.2-0.5%", "reply_rate": "0.1-0.2%"}}
            }},
            "correlations": [
                {{"feature1": "follower_count", "feature2": "engagement_rate", "correlation": -0.3, "insight": "larger accounts often have lower engagement rates"}},
                {{"feature1": "media_presence", "feature2": "retweets", "correlation": 0.6, "insight": "visual content drives sharing"}}
            ],
            "recommendations": {{
                "immediate_actions": [
                    {{"action": "optimize_posting_time", "expected_improvement": "15-25%", "difficulty": "easy"}},
                    {{"action": "add_relevant_media", "expected_improvement": "30-50%", "difficulty": "medium"}}
                ],
                "long_term_strategies": [
                    {{"strategy": "build_community_engagement", "timeline": "3-6 months", "expected_roi": "high"}},
                    {{"strategy": "develop_content_series", "timeline": "1-3 months", "expected_roi": "medium"}}
                ]
            }},
            "audience_insights": {{
                "peak_activity": {{"days": ["Tuesday", "Wednesday"], "hours": ["14:00-16:00"]}},
                "content_preferences": ["educational", "entertaining", "news"],
                "engagement_style": "prefers_visual_content_with_clear_call_to_action"
            }},
            "insights": "Strategic insights for maximizing engagement and reach"
        }}
        """
    
    @staticmethod
    def custom_analysis(tweet_texts: List[str], custom_prompt: str) -> str:
        return f"""
        {custom_prompt}
        
        Analyze the following {len(tweet_texts)} tweets according to the above requirements:
        {chr(10).join([f"{i+1}. {text}" for i, text in enumerate(tweet_texts[:50])])}
        
        Respond in JSON format with structured results that address the specific analysis requested.
        Ensure your response includes:
        1. Clear categorization of findings
        2. Quantitative metrics where applicable
        3. Qualitative insights and interpretations
        4. Actionable recommendations
        5. Supporting evidence from the tweet data
        
        Structure your response as:
        {{
            "analysis_type": "custom_analysis",
            "findings": {{
                "key_metrics": {{}},
                "patterns": [],
                "insights": []
            }},
            "recommendations": [],
            "supporting_evidence": [],
            "conclusion": "Summary of key findings and implications"
        }}
        """
    
    @staticmethod
    def get_system_prompt() -> str:
        return """You are an expert social media analyst specializing in Twitter/X data analysis. 
        
        Your expertise includes:
        - Sentiment analysis and emotional intelligence
        - Topic modeling and trend identification
        - Social media engagement optimization
        - Content classification and categorization
        - Named entity recognition and relationship mapping
        - Viral content pattern recognition
        - Audience behavior analysis
        
        Guidelines for your analysis:
        1. Always provide data-driven insights backed by evidence from the tweets
        2. Use quantitative metrics whenever possible (percentages, scores, counts)
        3. Identify actionable patterns that can inform strategy
        4. Consider context, timing, and social dynamics in your analysis
        5. Highlight both opportunities and risks in your findings
        6. Provide clear, structured responses in valid JSON format
        7. Include confidence scores for subjective assessments
        8. Explain your reasoning for key insights
        
        Respond with detailed, accurate analysis that provides real value for social media strategy and understanding."""