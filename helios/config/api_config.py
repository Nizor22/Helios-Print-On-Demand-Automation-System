"""
API Configuration for Helios

Centralized configuration for all external API integrations.
"""

import os
from typing import Optional

class APIConfig:
    """Centralized API configuration management"""
    
    def __init__(self):
        # Google Trends API
        self.google_trends_api_key = os.getenv("GOOGLE_TRENDS_API_KEY")
        
        # Twitter API
        self.twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        
        # Reddit API
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        
        # News API
        self.news_api_key = os.getenv("NEWS_API_KEY")
        
        # TikTok API
        self.tiktok_api_key = os.getenv("TIKTOK_API_KEY")
        
        # Google Cloud (Vertex AI)
        self.google_project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.google_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
    def get_google_trends_config(self) -> Optional[dict]:
        """Get Google Trends API configuration"""
        if not self.google_trends_api_key:
            return None
        return {
            "api_key": self.google_trends_api_key,
            "timeout": 30
        }
    
    def get_twitter_config(self) -> Optional[dict]:
        """Get Twitter API configuration"""
        if not self.twitter_bearer_token:
            return None
        return {
            "bearer_token": self.twitter_bearer_token,
            "api_key": self.twitter_api_key,
            "api_secret": self.twitter_api_secret
        }
    
    def get_reddit_config(self) -> Optional[dict]:
        """Get Reddit API configuration"""
        if not self.reddit_client_id:
            return None
        return {
            "client_id": self.reddit_client_id,
            "client_secret": self.reddit_client_secret
        }
    
    def get_news_config(self) -> Optional[dict]:
        """Get News API configuration"""
        if not self.news_api_key:
            return None
        return {
            "api_key": self.news_api_key,
            "sources": "all"
        }
    
    def get_tiktok_config(self) -> Optional[dict]:
        """Get TikTok API configuration"""
        if not self.tiktok_api_key:
            return None
        return {
            "api_key": self.tiktok_api_key
        }
    
    def get_google_cloud_config(self) -> Optional[dict]:
        """Get Google Cloud configuration"""
        if not self.google_project_id:
            return None
        return {
            "project_id": self.google_project_id,
            "location": self.google_location
        }
    
    def validate_configuration(self) -> dict:
        """Validate API configuration and return status"""
        status = {
            "google_trends": bool(self.google_trends_api_key),
            "twitter": bool(self.twitter_bearer_token),
            "reddit": bool(self.reddit_client_id),
            "news": bool(self.news_api_key),
            "tiktok": bool(self.tiktok_api_key),
            "google_cloud": bool(self.google_project_id)
        }
        
        configured_apis = sum(status.values())
        total_apis = len(status)
        
        return {
            "status": status,
            "configured_count": configured_apis,
            "total_count": total_apis,
            "configuration_percentage": f"{(configured_apis/total_apis)*100:.1f}%"
        }

# Global instance
api_config = APIConfig()
