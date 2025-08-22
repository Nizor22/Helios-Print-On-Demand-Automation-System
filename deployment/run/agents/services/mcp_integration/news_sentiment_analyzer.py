"""
News Sentiment Analyzer for Helios Autonomous Store
Integrates with MCP framework for news analysis, sentiment detection, and trend relevance
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
from loguru import logger

from .mcp_client import GoogleMCPClient


@dataclass
class NewsArticle:
    """News article data structure"""
    title: str
    content: str
    url: str
    source: str
    published_at: datetime
    sentiment_score: float
    relevance_score: float
    category: str
    keywords: List[str]
    summary: str = None
    image_url: str = None


@dataclass
class SentimentAnalysis:
    """Sentiment analysis results"""
    overall_sentiment: float
    sentiment_label: str
    confidence: float
    emotion_breakdown: Dict[str, float]
    subjectivity_score: float
    sentiment_trends: List[Dict[str, Any]]


@dataclass
class NewsTrend:
    """News trend data structure"""
    topic: str
    volume: int
    sentiment_distribution: Dict[str, float]
    top_sources: List[str]
    trending_keywords: List[str]
    relevance_score: float
    timestamp: datetime


class NewsSentimentAnalyzer:
    """
    News sentiment analyzer using MCP integration
    Provides comprehensive news analysis and sentiment detection
    """
    
    def __init__(self, mcp_client: GoogleMCPClient = None):
        self.mcp_client = mcp_client or GoogleMCPClient()
        self.supported_sources = [
            "google_news", "rss_feeds", "news_api", "reddit_news", "twitter_news"
        ]
        
        # Sentiment thresholds
        self.sentiment_thresholds = {
            "very_positive": 0.8,
            "positive": 0.3,
            "neutral": (-0.2, 0.2),
            "negative": -0.3,
            "very_negative": -0.8
        }
        
        # Emotion categories
        self.emotion_categories = [
            "joy", "sadness", "anger", "fear", "surprise", "disgust", "trust", "anticipation"
        ]
        
        # News categories
        self.news_categories = [
            "business", "technology", "politics", "entertainment", "sports",
            "health", "science", "world", "national", "local"
        ]
        
        logger.info("✅ News Sentiment Analyzer initialized")
    
    async def analyze_news_sentiment(
        self,
        query: str,
        sources: List[str] = None,
        time_range: str = "7d",
        limit: int = 50
    ) -> Dict[str, Any]:
        """Analyze news sentiment for a specific query"""
        
        try:
            # Use MCP client for news analysis
            result = await self.mcp_client.analyze_news(
                query=query,
                sources=sources or ["google_news"],
                time_range=time_range,
                sentiment_analysis=True
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_news_analysis(result, query, sources, time_range)
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error analyzing news sentiment: {e}")
            return {"error": str(e), "query": query, "sources": sources}
    
    async def get_trending_news(
        self,
        category: str = "all",
        geo: str = "US",
        time_range: str = "24h",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get trending news for a specific category and location"""
        
        try:
            # Use MCP client for trending news
            result = await self.mcp_client.analyze_news(
                query="trending",
                sources=["google_news"],
                time_range=time_range,
                sentiment_analysis=True
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_trending_news(result, category, geo, time_range)
            
            # Filter by category if specified
            if category != "all" and "articles" in enhanced_result:
                enhanced_result["articles"] = [
                    article for article in enhanced_result["articles"]
                    if article.get("category") == category
                ][:limit]
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error getting trending news: {e}")
            return {"error": str(e), "category": category, "geo": geo}
    
    async def analyze_source_sentiment(
        self,
        source: str,
        time_range: str = "7d",
        limit: int = 100
    ) -> Dict[str, Any]:
        """Analyze sentiment patterns for a specific news source"""
        
        if source not in self.supported_sources:
            return {"error": f"Unsupported source: {source}"}
        
        try:
            # Use MCP client for source analysis
            result = await self.mcp_client.analyze_news(
                query="",
                sources=[source],
                time_range=time_range,
                sentiment_analysis=True
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_source_analysis(result, source, time_range)
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error analyzing source sentiment: {e}")
            return {"error": str(e), "source": source}
    
    async def compare_news_sentiment(
        self,
        queries: List[str],
        sources: List[str] = None,
        time_range: str = "7d"
    ) -> Dict[str, Any]:
        """Compare news sentiment across multiple queries"""
        
        if len(queries) < 2:
            return {"error": "At least 2 queries required for comparison"}
        
        if len(queries) > 5:
            return {"error": "Maximum 5 queries allowed for comparison"}
        
        try:
            # Use MCP client for sentiment comparison
            comparison_data = []
            for query in queries:
                result = await self.mcp_client.analyze_news(
                    query=query,
                    sources=sources or ["google_news"],
                    time_range=time_range,
                    sentiment_analysis=True
                )
                comparison_data.append({
                    "query": query,
                    "data": result
                })
            
            # Process and enhance the comparison
            enhanced_comparison = await self._process_sentiment_comparison(
                comparison_data, queries, sources, time_range
            )
            return enhanced_comparison
            
        except Exception as e:
            logger.error(f"Error comparing news sentiment: {e}")
            return {"error": str(e), "queries": queries, "sources": sources}
    
    async def detect_news_trends(
        self,
        seed_keywords: List[str] = None,
        categories: List[str] = None,
        time_range: str = "7d",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Detect emerging news trends based on sentiment patterns"""
        
        try:
            # Use MCP client for trend detection
            result = await self.mcp_client.discover_trends(
                seed_keywords=seed_keywords or [],
                categories=categories or ["all"],
                time_range=time_range
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_news_trends(result, seed_keywords, categories)
            
            # Limit results if specified
            if "trends" in enhanced_result and limit:
                enhanced_result["trends"] = enhanced_result["trends"][:limit]
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error detecting news trends: {e}")
            return {"error": str(e), "seed_keywords": seed_keywords, "categories": categories}
    
    async def analyze_sentiment_evolution(
        self,
        query: str,
        time_range: str = "30d",
        interval: str = "1d"
    ) -> Dict[str, Any]:
        """Analyze how sentiment evolves over time for a specific query"""
        
        try:
            # Get sentiment data over time
            sentiment_data = await self.analyze_news_sentiment(query, time_range=time_range)
            
            if "error" in sentiment_data:
                return sentiment_data
            
            # Analyze sentiment evolution
            evolution_analysis = await self._analyze_sentiment_evolution_data(
                sentiment_data, query, time_range, interval
            )
            return evolution_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment evolution: {e}")
            return {"error": str(e), "query": query, "time_range": time_range}
    
    async def get_sentiment_summary(
        self,
        articles: List[NewsArticle]
    ) -> Dict[str, Any]:
        """Generate sentiment summary for a collection of articles"""
        
        if not articles:
            return {"error": "No articles provided for analysis"}
        
        try:
            # Calculate overall sentiment metrics
            total_articles = len(articles)
            sentiment_scores = [article.sentiment_score for article in articles]
            relevance_scores = [article.relevance_score for article in articles]
            
            # Calculate summary statistics
            avg_sentiment = sum(sentiment_scores) / total_articles
            avg_relevance = sum(relevance_scores) / total_articles
            
            # Categorize sentiment distribution
            sentiment_distribution = self._categorize_sentiment_distribution(sentiment_scores)
            
            # Analyze source diversity
            sources = list(set(article.source for article in articles))
            source_diversity = len(sources) / total_articles
            
            # Analyze category distribution
            category_distribution = {}
            for article in articles:
                category = article.category
                if category not in category_distribution:
                    category_distribution[category] = 0
                category_distribution[category] += 1
            
            # Normalize category distribution
            for category in category_distribution:
                category_distribution[category] /= total_articles
            
            return {
                "summary": {
                    "total_articles": total_articles,
                    "average_sentiment": avg_sentiment,
                    "average_relevance": avg_relevance,
                    "sentiment_distribution": sentiment_distribution,
                    "source_diversity": source_diversity,
                    "category_distribution": category_distribution
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating sentiment summary: {e}")
            return {"error": str(e)}
    
    async def _process_news_analysis(
        self,
        data: Dict[str, Any],
        query: str,
        sources: List[str],
        time_range: str
    ) -> Dict[str, Any]:
        """Process news analysis data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "query": query,
                "sources": sources or ["google_news"],
                "time_range": time_range,
                "timestamp": datetime.now().isoformat(),
                "data_source": "News API via MCP"
            }
            
            # Add sentiment analysis if articles exist
            if "articles" in enhanced_data:
                for article in enhanced_data["articles"]:
                    article["sentiment_label"] = self._get_sentiment_label(
                        article.get("sentiment_score", 0)
                    )
                    article["relevance_score"] = self._calculate_relevance_score(
                        article, query
                    )
                    article["category"] = self._categorize_article(article)
            
            # Add overall sentiment summary
            if "articles" in enhanced_data:
                enhanced_data["sentiment_summary"] = await self._generate_article_summary(
                    enhanced_data["articles"]
                )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing news analysis: {e}")
            return data
    
    async def _process_trending_news(
        self,
        data: Dict[str, Any],
        category: str,
        geo: str,
        time_range: str
    ) -> Dict[str, Any]:
        """Process trending news data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "category": category,
                "geo": geo,
                "time_range": time_range,
                "timestamp": datetime.now().isoformat(),
                "data_source": "News API via MCP"
            }
            
            # Add trend scoring if articles exist
            if "articles" in enhanced_data:
                for article in enhanced_data["articles"]:
                    article["trend_score"] = self._calculate_trend_score(article)
                    article["viral_potential"] = self._calculate_viral_potential(article)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing trending news: {e}")
            return data
    
    async def _process_source_analysis(
        self,
        data: Dict[str, Any],
        source: str,
        time_range: str
    ) -> Dict[str, Any]:
        """Process source analysis data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "source": source,
                "time_range": time_range,
                "timestamp": datetime.now().isoformat(),
                "data_source": "News API via MCP"
            }
            
            # Add source-specific analysis if articles exist
            if "articles" in enhanced_data:
                enhanced_data["source_analysis"] = await self._analyze_source_patterns(
                    enhanced_data["articles"], source
                )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing source analysis: {e}")
            return data
    
    async def _process_sentiment_comparison(
        self,
        comparison_data: List[Dict[str, Any]],
        queries: List[str],
        sources: List[str],
        time_range: str
    ) -> Dict[str, Any]:
        """Process sentiment comparison data"""
        
        try:
            enhanced_comparison = {
                "queries": queries,
                "sources": sources or ["google_news"],
                "time_range": time_range,
                "timestamp": datetime.now().isoformat(),
                "data_source": "News API via MCP",
                "comparison_data": comparison_data,
                "analysis": {}
            }
            
            # Add comparative analysis
            if comparison_data:
                enhanced_comparison["analysis"] = await self._analyze_sentiment_comparison_data(
                    comparison_data, queries
                )
            
            return enhanced_comparison
            
        except Exception as e:
            logger.error(f"Error processing sentiment comparison: {e}")
            return {"error": str(e), "queries": queries}
    
    async def _process_news_trends(
        self,
        data: Dict[str, Any],
        seed_keywords: List[str],
        categories: List[str]
    ) -> Dict[str, Any]:
        """Process news trends data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "seed_keywords": seed_keywords,
                "categories": categories,
                "timestamp": datetime.now().isoformat(),
                "data_source": "News API via MCP"
            }
            
            # Add trend insights if trends exist
            if "trends" in enhanced_data:
                enhanced_data["trend_insights"] = await self._analyze_news_trend_insights(
                    enhanced_data["trends"], seed_keywords, categories
                )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing news trends: {e}")
            return data
    
    async def _analyze_sentiment_evolution_data(
        self,
        sentiment_data: Dict[str, Any],
        query: str,
        time_range: str,
        interval: str
    ) -> Dict[str, Any]:
        """Analyze sentiment evolution over time"""
        
        try:
            if "articles" not in sentiment_data:
                return {"error": "No articles data available"}
            
            articles = sentiment_data["articles"]
            
            # Group articles by time intervals
            time_groups = self._group_articles_by_time(articles, interval)
            
            # Calculate sentiment trends for each time group
            evolution_data = []
            for time_group, group_articles in time_groups.items():
                if group_articles:
                    avg_sentiment = sum(
                        article.get("sentiment_score", 0) for article in group_articles
                    ) / len(group_articles)
                    
                    evolution_data.append({
                        "time_period": time_group,
                        "average_sentiment": avg_sentiment,
                        "article_count": len(group_articles),
                        "sentiment_label": self._get_sentiment_label(avg_sentiment)
                    })
            
            # Sort by time period
            evolution_data.sort(key=lambda x: x["time_period"])
            
            # Calculate evolution metrics
            if len(evolution_data) >= 2:
                first_sentiment = evolution_data[0]["average_sentiment"]
                last_sentiment = evolution_data[-1]["average_sentiment"]
                sentiment_change = last_sentiment - first_sentiment
                
                evolution_metrics = {
                    "overall_change": sentiment_change,
                    "change_direction": "improving" if sentiment_change > 0 else "declining",
                    "change_magnitude": abs(sentiment_change),
                    "volatility": self._calculate_sentiment_volatility(evolution_data)
                }
            else:
                evolution_metrics = {"status": "insufficient_data"}
            
            return {
                "query": query,
                "time_range": time_range,
                "interval": interval,
                "evolution_data": evolution_data,
                "evolution_metrics": evolution_metrics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment evolution data: {e}")
            return {"error": str(e), "query": query}
    
    def _get_sentiment_label(self, sentiment_score: float) -> str:
        """Get sentiment label based on score"""
        
        if sentiment_score >= self.sentiment_thresholds["very_positive"]:
            return "very_positive"
        elif sentiment_score >= self.sentiment_thresholds["positive"]:
            return "positive"
        elif (self.sentiment_thresholds["neutral"][0] <= 
              sentiment_score <= self.sentiment_thresholds["neutral"][1]):
            return "neutral"
        elif sentiment_score >= self.sentiment_thresholds["negative"]:
            return "negative"
        else:
            return "very_negative"
    
    def _calculate_relevance_score(self, article: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for an article"""
        
        # Simple relevance scoring based on query similarity
        query_words = set(query.lower().split())
        title_words = set(article.get("title", "").lower().split())
        content_words = set(article.get("content", "").lower().split())
        
        if not query_words:
            return 0.0
        
        # Title relevance (weighted higher)
        title_relevance = 0.0
        if title_words:
            intersection = len(query_words.intersection(title_words))
            union = len(query_words.union(title_words))
            title_relevance = intersection / union if union > 0 else 0.0
        
        # Content relevance
        content_relevance = 0.0
        if content_words:
            intersection = len(query_words.intersection(content_words))
            union = len(query_words.union(content_words))
            content_relevance = intersection / union if union > 0 else 0.0
        
        # Weighted relevance score
        relevance_score = (title_relevance * 0.7) + (content_relevance * 0.3)
        return min(max(relevance_score, 0.0), 1.0)
    
    def _categorize_article(self, article: Dict[str, Any]) -> str:
        """Categorize an article based on its content"""
        
        # Simple categorization based on keywords
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()
        text = f"{title} {content}"
        
        category_keywords = {
            "business": ["business", "economy", "finance", "market", "stock", "company"],
            "technology": ["tech", "technology", "software", "app", "digital", "ai", "machine learning"],
            "politics": ["politics", "government", "election", "policy", "congress", "senate"],
            "entertainment": ["entertainment", "movie", "music", "celebrity", "hollywood"],
            "sports": ["sports", "football", "basketball", "baseball", "soccer", "game"],
            "health": ["health", "medical", "disease", "treatment", "hospital", "doctor"],
            "science": ["science", "research", "study", "discovery", "experiment"],
            "world": ["world", "international", "global", "foreign", "country"],
            "national": ["national", "domestic", "local", "city", "state"]
        }
        
        # Find the best matching category
        best_category = "general"
        best_score = 0.0
        
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > best_score:
                best_score = score
                best_category = category
        
        return best_category
    
    def _categorize_sentiment_distribution(self, sentiment_scores: List[float]) -> Dict[str, float]:
        """Categorize sentiment distribution"""
        
        total_scores = len(sentiment_scores)
        if total_scores == 0:
            return {}
        
        distribution = {
            "very_positive": 0.0,
            "positive": 0.0,
            "neutral": 0.0,
            "negative": 0.0,
            "very_negative": 0.0
        }
        
        for score in sentiment_scores:
            label = self._get_sentiment_label(score)
            distribution[label] += 1.0
        
        # Normalize to percentages
        for label in distribution:
            distribution[label] /= total_scores
        
        return distribution
    
    def _calculate_trend_score(self, article: Dict[str, Any]) -> float:
        """Calculate trend score for an article"""
        
        score = 0.0
        
        # Sentiment score contribution
        sentiment_score = article.get("sentiment_score", 0)
        score += (sentiment_score + 1) * 0.3  # Convert -1 to 1 range to 0 to 0.6
        
        # Relevance score contribution
        relevance_score = article.get("relevance_score", 0)
        score += relevance_score * 0.4
        
        # Recency bonus (if available)
        if "published_at" in article:
            published_at = article["published_at"]
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    hours_ago = (datetime.now() - published_at).total_seconds() / 3600
                    if hours_ago < 24:
                        score += 0.3  # Recent article bonus
                except:
                    pass
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_viral_potential(self, article: Dict[str, Any]) -> str:
        """Calculate viral potential for an article"""
        
        trend_score = article.get("trend_score", 0)
        sentiment_score = article.get("sentiment_score", 0)
        
        if trend_score > 0.8 and sentiment_score > 0.5:
            return "high"
        elif trend_score > 0.6 and sentiment_score > 0.0:
            return "medium"
        else:
            return "low"
    
    def _group_articles_by_time(self, articles: List[Dict[str, Any]], interval: str) -> Dict[str, List[Dict[str, Any]]]:
        """Group articles by time intervals"""
        
        # Placeholder for time grouping logic
        # This would be implemented based on the specific interval format
        return {"recent": articles}
    
    def _calculate_sentiment_volatility(self, evolution_data: List[Dict[str, Any]]) -> float:
        """Calculate sentiment volatility over time"""
        
        if len(evolution_data) < 2:
            return 0.0
        
        sentiments = [data["average_sentiment"] for data in evolution_data]
        mean_sentiment = sum(sentiments) / len(sentiments)
        
        variance = sum((s - mean_sentiment) ** 2 for s in sentiments) / len(sentiments)
        volatility = variance ** 0.5
        
        return volatility
    
    async def _generate_article_summary(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary for a collection of articles"""
        
        # Placeholder for article summary generation
        return {"status": "summary_pending", "article_count": len(articles)}
    
    async def _analyze_source_patterns(self, articles: List[Dict[str, Any]], source: str) -> Dict[str, Any]:
        """Analyze patterns for a specific news source"""
        
        # Placeholder for source pattern analysis
        return {"status": "analysis_pending", "source": source, "article_count": len(articles)}
    
    async def _analyze_sentiment_comparison_data(
        self,
        comparison_data: List[Dict[str, Any]],
        queries: List[str]
    ) -> Dict[str, Any]:
        """Analyze sentiment comparison data"""
        
        # Placeholder for comparison analysis
        return {"status": "analysis_pending", "queries": queries}
    
    async def _analyze_news_trend_insights(
        self,
        trends: List[Dict[str, Any]],
        seed_keywords: List[str],
        categories: List[str]
    ) -> Dict[str, Any]:
        """Analyze news trend insights"""
        
        # Placeholder for trend insights
        return {"status": "analysis_pending", "trends_count": len(trends)}
    
    async def analyze_trending_topics(
        self,
        categories: List[str] = None,
        time_window: str = "7d",
        limit: int = 15
    ) -> Dict[str, Any]:
        """Analyze trending topics from news sources"""
        try:
            if categories is None:
                categories = ["business", "technology", "entertainment"]
            
            # Get trending news for each category
            trending_topics = []
            for category in categories[:3]:  # Limit to 3 categories
                try:
                    news_data = await self.get_trending_news(
                        category=category,
                        time_range=time_window,
                        limit=limit // len(categories)
                    )
                    
                    if news_data.get("status") == "success" and "articles" in news_data:
                        for article in news_data["articles"]:
                            trending_topics.append({
                                "topic": article.get("title", "Unknown Topic"),
                                "category": category,
                                "sentiment": article.get("sentiment_score", 0),
                                "volume": 1,  # Single article
                                "trend_score": article.get("trend_score", 0),
                                "source": article.get("source", "news"),
                                "url": article.get("url"),
                                "published": article.get("published")
                            })
                except Exception as e:
                    logger.warning(f"Failed to get trending news for category {category}: {e}")
                    continue
            
            # Sort by trend score and limit results
            trending_topics.sort(key=lambda x: x.get("trend_score", 0), reverse=True)
            trending_topics = trending_topics[:limit]
            
            return {
                "status": "success",
                "trending_topics": trending_topics,
                "categories": categories,
                "time_window": time_window,
                "total_topics": len(trending_topics),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trending topics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "trending_topics": [],
                "categories": categories or [],
                "time_window": time_window
            }
    
    async def close(self):
        """Clean up resources"""
        if self.mcp_client:
            await self.mcp_client.close()
        logger.info("✅ News Sentiment Analyzer closed")


# Convenience functions for external use
async def analyze_news_sentiment(
    query: str,
    sources: List[str] = None,
    time_range: str = "7d"
) -> Dict[str, Any]:
    """Convenience function to analyze news sentiment"""
    
    analyzer = NewsSentimentAnalyzer()
    try:
        return await analyzer.analyze_news_sentiment(query, sources, time_range)
    finally:
        await analyzer.close()


async def get_trending_news(
    category: str = "all",
    geo: str = "US",
    time_range: str = "24h"
) -> Dict[str, Any]:
    """Convenience function to get trending news"""
    
    analyzer = NewsSentimentAnalyzer()
    try:
        return await analyzer.get_trending_news(category, geo, time_range)
    finally:
        await analyzer.close()


async def compare_news_sentiment(
    queries: List[str],
    sources: List[str] = None,
    time_range: str = "7d"
) -> Dict[str, Any]:
    """Convenience function to compare news sentiment"""
    
    analyzer = NewsSentimentAnalyzer()
    try:
        return await analyzer.compare_news_sentiment(queries, sources, time_range)
    finally:
        await analyzer.close()


async def detect_news_trends(
    seed_keywords: List[str] = None,
    categories: List[str] = None,
    time_range: str = "7d"
) -> Dict[str, Any]:
    """Convenience function to detect news trends"""
    
    analyzer = NewsSentimentAnalyzer()
    try:
        return await analyzer.detect_news_trends(seed_keywords, categories, time_range)
    finally:
        await analyzer.close()
