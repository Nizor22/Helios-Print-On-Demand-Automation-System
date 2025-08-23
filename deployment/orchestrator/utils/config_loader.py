"""
Configuration Management Utility for Helios Autonomous Store
Handles environment variables, configuration files, and secrets management
"""

import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Configuration loader for Helios Autonomous Store
    Manages environment variables, config files, and Google Secret Manager
    """
    
    def __init__(self, project_id: str = None, config_path: str = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.config_path = config_path or "config"
        self.secret_client = None
        self._config_cache = {}
        
        # Initialize Secret Manager client if project_id is available
        if self.project_id:
            try:
                self.secret_client = secretmanager.SecretManagerServiceClient()
                logger.info(f"Initialized Secret Manager client for project: {self.project_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize Secret Manager client: {str(e)}")
                self.secret_client = None
    
    def load_environment_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        
        config = {
            # Google Cloud Configuration (Primary)
            "google_cloud": {
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "region": os.getenv("GOOGLE_CLOUD_REGION", "us-central1"),
                "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
                "service_account_json": os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            },
            
            # Firebase/Firestore Configuration (Primary Data Store)
            "firebase": {
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "database": os.getenv("FIRESTORE_DATABASE", "helios-data"),
                "enabled": bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
            },
            
            # Cloud Storage Configuration (Primary Asset Store)
            "cloud_storage": {
                "trend_analysis_bucket": os.getenv("TREND_ANALYSIS_BUCKET", "trend-analysis-data"),
                "product_assets_bucket": os.getenv("PRODUCT_ASSETS_BUCKET", "helios-product-assets-658997361183"),
                "enabled": bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
            },
            
            # Google Services Configuration (Optional Fallbacks)
            "google_services": {
                "sheets_tracking_id": os.getenv("GOOGLE_SHEETS_TRACKING_ID"),
                "drive_folder_id": os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
                "gmail_enabled": os.getenv("GMAIL_ENABLED", "false").lower() == "true",
                "enabled": bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") and os.getenv("GOOGLE_SHEETS_TRACKING_ID"))
            },
            
            # MCP Configuration (Required)
            "mcp": {
                "server_url": os.getenv("GOOGLE_MCP_URL", "http://localhost:8080"),
                "auth_token": os.getenv("GOOGLE_MCP_AUTH_TOKEN"),
                "enabled": os.getenv("GOOGLE_MCP_ENABLED", "true").lower() == "true"
            },
            
            # External APIs Configuration
            "external_apis": {
                "printify": {
                    "api_token": os.getenv("PRINTIFY_API_TOKEN"),
                    "shop_id": os.getenv("PRINTIFY_SHOP_ID"),
                    "enabled": bool(os.getenv("PRINTIFY_API_TOKEN"))
                },
                "etsy": {
                    "api_key": os.getenv("ETSY_API_KEY"),
                    "enabled": bool(os.getenv("ETSY_API_KEY"))
                },
                "gemini": {
                    "api_key": os.getenv("GEMINI_API_KEY"),
                    "enabled": bool(os.getenv("GEMINI_API_KEY"))
                }
            },
            
            # Performance Configuration
            "performance": {
                "min_opportunity_score": float(os.getenv("MIN_OPPORTUNITY_SCORE", "5.0")),
                "min_audience_confidence": float(os.getenv("MIN_AUDIENCE_CONFIDENCE", "7.0")),
                "min_profit_margin": float(os.getenv("MIN_PROFIT_MARGIN", "0.35")),
                "max_execution_time": int(os.getenv("MAX_EXECUTION_TIME", "300")),
                "enable_parallel_processing": os.getenv("ENABLE_PARALLEL_PROCESSING", "true").lower() == "true",
                "enable_batch_creation": os.getenv("ENABLE_BATCH_CREATION", "true").lower() == "true",
                "enable_adaptive_learning": os.getenv("ENABLE_ADAPTIVE_LEARNING", "true").lower() == "true",
                "enable_auto_optimization": os.getenv("ENABLE_AUTO_OPTIMIZATION", "true").lower() == "true"
            },
            
            # Safety Configuration
            "safety": {
                "allow_live_publishing": os.getenv("ALLOW_LIVE_PUBLISHING", "false").lower() == "true",
                "content_moderation_enabled": os.getenv("CONTENT_MODERATION_ENABLED", "true").lower() == "true",
                "ethical_guard_enabled": os.getenv("ETHICAL_GUARD_ENABLED", "true").lower() == "true"
            },
            
            # Printify Product Configuration
            "printify": {
                "blueprint_id": os.getenv("BLUEPRINT_ID", "482"),
                "print_provider_id": os.getenv("PRINT_PROVIDER_ID", "1"),
                "default_colors": os.getenv("DEFAULT_COLORS", "white,black").split(","),
                "default_sizes": os.getenv("DEFAULT_SIZES", "S,M,L,XL,2XL").split(","),
                "default_draft": os.getenv("DEFAULT_DRAFT", "true").lower() == "true",
                "default_margin": float(os.getenv("DEFAULT_MARGIN", "0.6")),
                "dry_run": os.getenv("DRY_RUN", "false").lower() == "true"
            },
            
            # AI Model Configuration
            "ai_models": {
                "gemini_pro": {
                    "model_name": "gemini-1.5-pro",
                    "max_tokens": 8192,
                    "temperature": 0.7
                },
                "gemini_flash": {
                    "model_name": "gemini-1.5-flash",
                    "max_tokens": 8192,
                    "temperature": 0.8
                },
                "gemini_ultra": {
                    "model_name": "gemini-1.0-ultra",
                    "max_tokens": 32768,
                    "temperature": 0.5
                }
            },
            
            # Cache Configuration
            "caching": {
                "trend_data_ttl": int(os.getenv("TREND_DATA_TTL", "3600")),  # 1 hour
                "printify_catalog_ttl": int(os.getenv("PRINTIFY_CATALOG_TTL", "86400")),  # 24 hours
                "generated_content_ttl": int(os.getenv("GENERATED_CONTENT_TTL", "300")),  # 5 minutes
                "api_response_ttl": int(os.getenv("API_RESPONSE_TTL", "300"))  # 5 minutes
            },
            
            # Monitoring Configuration
            "monitoring": {
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "enable_cloud_monitoring": os.getenv("ENABLE_CLOUD_MONITORING", "true").lower() == "true",
                "enable_tracing": os.getenv("ENABLE_TRACING", "true").lower() == "true",
                "metrics_export_interval": int(os.getenv("METRICS_EXPORT_INTERVAL", "60"))  # seconds
            }
        }
        
        # Validate required configuration
        self._validate_config(config)
        
        return config
    
    def load_config_file(self, filename: str, environment: str = None) -> Dict[str, Any]:
        """Load configuration from YAML/JSON file"""
        
        if filename in self._config_cache:
            return self._config_cache[filename]
        
        config_path = Path(self.config_path)
        file_path = config_path / filename
        
        if not file_path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    config = yaml.safe_load(f)
                elif filename.endswith('.json'):
                    config = json.load(f)
                else:
                    logger.error(f"Unsupported config file format: {filename}")
                    return {}
            
            # Apply environment-specific overrides
            if environment and isinstance(config, dict):
                env_config = config.get(environment, {})
                if env_config:
                    config.update(env_config)
            
            self._config_cache[filename] = config
            logger.info(f"Loaded config file: {filename}")
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config file {filename}: {str(e)}")
            return {}
    
    def get_secret(self, secret_name: str, version: str = "latest") -> Optional[str]:
        """Retrieve secret from Google Secret Manager"""
        
        if not self.secret_client:
            logger.warning("Secret Manager client not initialized")
            return None
        
        try:
            secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            response = self.secret_client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8")
            
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
            return None
    
    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'performance.min_opportunity_score')"""
        
        # First try environment variable
        env_key = key_path.upper().replace('.', '_')
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._parse_env_value(env_value)
        
        # Then try config files
        config = self.load_environment_config()
        
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def _parse_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Parse environment variable value to appropriate type"""
        
        # Try to convert to boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try to convert to int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate required configuration values"""
        
        required_fields = [
            "google_cloud.project_id",
            "external_apis.printify.api_token",
            "external_apis.printify.shop_id"
        ]
        
        missing_fields = []
        
        for field_path in required_fields:
            keys = field_path.split('.')
            value = config
            
            try:
                for key in keys:
                    value = value[key]
                
                if not value:
                    missing_fields.append(field_path)
                    
            except (KeyError, TypeError):
                missing_fields.append(field_path)
        
        if missing_fields:
            logger.warning(f"Missing required configuration fields: {missing_fields}")
        
        # Validate performance thresholds
        performance = config.get("performance", {})
        if performance.get("min_opportunity_score", 0) < 0 or performance.get("min_opportunity_score", 0) > 10:
            logger.warning("MIN_OPPORTUNITY_SCORE should be between 0 and 10")
        
        if performance.get("min_profit_margin", 0) < 0 or performance.get("min_profit_margin", 0) > 1:
            logger.warning("MIN_PROFIT_MARGIN should be between 0 and 1")
    
    def reload_config(self) -> Dict[str, Any]:
        """Reload configuration and clear cache"""
        
        self._config_cache.clear()
        return self.load_environment_config()
    
    def export_config(self, format: str = "json") -> str:
        """Export current configuration to string format"""
        
        config = self.load_environment_config()
        
        if format.lower() == "yaml":
            return yaml.dump(config, default_flow_style=False, indent=2)
        else:
            return json.dumps(config, indent=2)
    
    def get_agent_prompts(self) -> Dict[str, str]:
        """Load agent system prompts from configuration"""
        
        prompts_config = self.load_config_file("agent_prompts.yaml")
        return prompts_config.get("prompts", {})
    
    def get_deployment_config(self, environment: str = "production") -> Dict[str, Any]:
        """Load deployment configuration for specified environment"""
        
        deployment_config = self.load_config_file("deployment.yaml", environment)
        return deployment_config.get("deployment", {})
    
    def get_testing_config(self) -> Dict[str, Any]:
        """Load testing configuration"""
        
        testing_config = self.load_config_file("testing.yaml")
        return testing_config.get("testing", {})


# Global configuration instance
_global_config = None


def get_config(project_id: str = None, config_path: str = None) -> ConfigLoader:
    """Get global configuration instance"""
    
    global _global_config
    
    if _global_config is None:
        _global_config = ConfigLoader(project_id, config_path)
    
    return _global_config


def reload_config() -> ConfigLoader:
    """Reload global configuration"""
    
    global _global_config
    
    if _global_config:
        _global_config.reload_config()
    
    return _global_config


# Example usage
if __name__ == "__main__":
    # Initialize config loader
    config_loader = ConfigLoader("helios-autonomous-store")
    
    # Load environment configuration
    env_config = config_loader.load_environment_config()
    print("Environment Configuration:")
    print(json.dumps(env_config, indent=2))
    
    # Get specific config values
    min_score = config_loader.get_config_value("performance.min_opportunity_score", 7.0)
    print(f"\nMinimum opportunity score: {min_score}")
    
    # Export configuration
    config_export = config_loader.export_config("yaml")
    print(f"\nConfiguration Export (YAML):\n{config_export}")
