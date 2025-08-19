from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, find_dotenv

def split_csv(value: str | None) -> list[str]:
    """Split a comma-separated string into a list, handling None values"""
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


@dataclass
class HeliosConfig:
    # Auth / IDs
    printify_api_token: str
    printify_shop_id: str

    # Product defaults
    blueprint_id: Optional[int] = None
    print_provider_id: Optional[int] = None
    default_colors: list[str] = None
    default_sizes: list[str] = None
    preferred_provider_name: Optional[str] = None

    # Behavior
    default_margin: float = 0.5
    default_draft: bool = True
    dry_run: bool = True

    # Paths
    project_root: Path = Path(__file__).resolve().parents[1]
    assets_dir: Path = project_root / "assets"
    fonts_dir: Path = assets_dir / "fonts"
    output_dir: Path = project_root / "output"

    # Google Cloud & MCP Integration
    google_api_key: Optional[str] = None  # Gemini
    gemini_model: Optional[str] = None
    google_cloud_project: Optional[str] = None
    google_service_account_json: Optional[str] = None
    google_drive_folder_id: Optional[str] = None
    assets_bucket: Optional[str] = None
    
    # Google MCP Configuration
    google_mcp_url: Optional[str] = None
    google_mcp_auth_token: Optional[str] = None
    
    # Google Sheets
    gsheet_id: Optional[str] = None
    
    # Performance Thresholds  
    min_opportunity_score: float = 5.0  # Lowered for enhanced early detection
    min_audience_confidence: float = 0.7  # 0-1 scale (70% confidence)
    min_profit_margin: float = 0.35
    max_execution_time: int = 300
    
    # Optimization Settings
    enable_parallel_processing: bool = True
    enable_batch_creation: bool = True
    enable_adaptive_learning: bool = True
    enable_auto_optimization: bool = True
    
    # Enhanced Trend Detection Settings (First-to-Market)
    enable_early_trend_detection: bool = True
    early_detection_velocity_threshold: float = 2.0
    early_detection_freshness_threshold: float = 0.7
    early_detection_viral_threshold: float = 0.6
    early_detection_min_signals: int = 3
    early_detection_max_trends: int = 20
    
    # Safety & Publishing
    allow_live_publishing: bool = False
    
    # Other integrations
    serpapi_key: Optional[str] = None
    
    # Google Cloud Infrastructure Settings
    google_cloud_region: str = "us-central1"
    google_cloud_location: str = "us-central1"
    
    # Vertex AI Configuration
    vertex_ai_project_id: Optional[str] = None
    vertex_ai_location: Optional[str] = None
    
    # Gemini AI Models
    gemini_pro_model: str = "gemini-1.5-pro"
    gemini_flash_model: str = "gemini-1.5-flash"
    gemini_ultra_model: str = "gemini-1.0-ultra"
    
    # Image Generation
    imagen_model: str = "imagen-3"
    image_resolution: str = "1024x1024"
    image_format: str = "PNG"
    image_quality: str = "high"
    
    # MCP Tools Configuration
    enable_google_trends_tool: bool = True
    enable_social_media_scanner: bool = True
    enable_news_analyzer: bool = True
    enable_competitor_intelligence: bool = True
    
    # MCP Tool Rate Limits
    google_trends_rate_limit: int = 100  # requests per hour
    social_media_rate_limit: int = 200   # requests per hour
    news_analyzer_rate_limit: int = 150  # requests per hour
    
    # External APIs Configuration
    etsy_api_key: Optional[str] = None
    printify_base_url: str = "https://api.printify.com/v1"
    printify_rate_limit: float = 0.5  # seconds between requests
    printify_retry_attempts: int = 3
    etsy_base_url: str = "https://openapi.etsy.com/v3"
    etsy_rate_limit: float = 1.0  # seconds between requests
    etsy_retry_attempts: int = 3
    
    # Google Workspace Integration
    google_sheets_tracking_id: Optional[str] = None
    google_drive_root_folder_id: Optional[str] = None
    sheets_update_frequency: str = "real_time"  # or "batch"
    
    # Performance Monitoring
    enable_performance_monitoring: bool = True
    enable_cloud_monitoring: bool = True
    enable_cloud_logging: bool = True
    enable_cloud_trace: bool = True
    
    # Caching Configuration
    enable_redis_caching: bool = True
    cache_ttl_trend_data: int = 3600  # 1 hour
    cache_ttl_printify_catalog: int = 86400  # 24 hours
    cache_ttl_api_responses: int = 300  # 5 minutes


def load_config(env_path: Optional[Path] = None) -> HeliosConfig:
    # Load .env if present; prefer .env values over any pre-exported ones
    if env_path is None:
        # Search from current working directory upward for a .env file
        found = find_dotenv(usecwd=True)
        if found:
            load_dotenv(found, override=True)
    else:
        load_dotenv(dotenv_path=env_path if env_path.exists() else None, override=True)

    api_token = os.getenv("PRINTIFY_API_TOKEN", "").strip()
    shop_id = os.getenv("PRINTIFY_SHOP_ID", "").strip()

    blueprint_id = os.getenv("BLUEPRINT_ID")
    provider_id = os.getenv("PRINT_PROVIDER_ID")

    def parse_int(value: Optional[str]) -> Optional[int]:
        try:
            return int(value) if value not in (None, "") else None
        except ValueError:
            return None

    def parse_float(value: Optional[str], default: float) -> float:
        try:
            return float(value) if value not in (None, "") else default
        except ValueError:
            return default

    def parse_bool(value: Optional[str], default: bool) -> bool:
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    colors = split_csv(os.getenv("DEFAULT_COLORS", "White,Black,Navy"))
    sizes = split_csv(os.getenv("DEFAULT_SIZES", "S,M,L,XL,2XL"))

    default_margin = parse_float(os.getenv("DEFAULT_MARGIN"), 0.5)
    default_draft = parse_bool(os.getenv("DEFAULT_DRAFT"), True)
    dry_run = parse_bool(os.getenv("DRY_RUN"), True)

    # Performance thresholds
    min_opportunity_score = parse_float(os.getenv("MIN_OPPORTUNITY_SCORE"), 5.0)  # Lowered for better trend detection
    min_audience_confidence = parse_float(os.getenv("MIN_AUDIENCE_CONFIDENCE"), 6.5) / 10.0  # Convert from 0-10 to 0-1 scale
    min_profit_margin = parse_float(os.getenv("MIN_PROFIT_MARGIN"), 0.35)
    max_execution_time = parse_int(os.getenv("MAX_EXECUTION_TIME")) or 300

    # Optimization settings
    enable_parallel_processing = parse_bool(os.getenv("ENABLE_PARALLEL_PROCESSING"), True)
    enable_batch_creation = parse_bool(os.getenv("ENABLE_BATCH_CREATION"), True)
    enable_adaptive_learning = parse_bool(os.getenv("ENABLE_ADAPTIVE_LEARNING"), True)
    enable_auto_optimization = parse_bool(os.getenv("ENABLE_AUTO_OPTIMIZATION"), True)

    # Safety settings
    allow_live_publishing = parse_bool(os.getenv("ALLOW_LIVE_PUBLISHING"), False)

    # Google Cloud settings
    google_cloud_region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    google_cloud_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    assets_bucket = os.getenv("ASSETS_BUCKET") or os.getenv("CLOUD_STORAGE_BUCKET")
    preferred_provider_name = os.getenv("PREFERRED_PROVIDER_NAME")

    cfg = HeliosConfig(
        printify_api_token=api_token,
        printify_shop_id=shop_id,
        blueprint_id=parse_int(blueprint_id),
        print_provider_id=parse_int(provider_id),
        default_colors=colors,
        default_sizes=sizes,
        preferred_provider_name=preferred_provider_name,
        default_margin=default_margin,
        default_draft=default_draft,
        dry_run=dry_run,
        
        # Google Cloud & MCP
        google_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        google_drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
        assets_bucket=assets_bucket,
        
        # Google MCP
        google_mcp_url=os.getenv("GOOGLE_MCP_URL"),
        google_mcp_auth_token=os.getenv("GOOGLE_MCP_AUTH_TOKEN"),
        
        # Google Sheets
        gsheet_id=os.getenv("GOOGLE_SHEETS_TRACKING_ID"),
        
        # Performance thresholds
        min_opportunity_score=min_opportunity_score,
        min_audience_confidence=min_audience_confidence,
        min_profit_margin=min_profit_margin,
        max_execution_time=max_execution_time,
        
        # Optimization settings
        enable_parallel_processing=enable_parallel_processing,
        enable_batch_creation=enable_batch_creation,
        enable_adaptive_learning=enable_adaptive_learning,
        enable_auto_optimization=enable_auto_optimization,
        
        # Safety settings
        allow_live_publishing=allow_live_publishing,
        
        # Other integrations
        serpapi_key=os.getenv("SERPAPI_API_KEY"),
        
        # Google Cloud Infrastructure
        google_cloud_region=google_cloud_region,
        google_cloud_location=google_cloud_location,
        vertex_ai_project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
        vertex_ai_location=google_cloud_location,
        
        # Gemini AI Models
        gemini_pro_model=os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro"),
        gemini_flash_model=os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash"),
        gemini_ultra_model=os.getenv("GEMINI_ULTRA_MODEL", "gemini-1.0-ultra"),
        
        # Image Generation
        imagen_model=os.getenv("IMAGEN_MODEL", "imagen-3"),
        image_resolution=os.getenv("IMAGE_RESOLUTION", "1024x1024"),
        image_format=os.getenv("IMAGE_FORMAT", "PNG"),
        image_quality=os.getenv("IMAGE_QUALITY", "high"),
        
        # MCP Tools
        enable_google_trends_tool=parse_bool(os.getenv("ENABLE_GOOGLE_TRENDS_TOOL"), True),
        enable_social_media_scanner=parse_bool(os.getenv("ENABLE_SOCIAL_MEDIA_SCANNER"), True),
        enable_news_analyzer=parse_bool(os.getenv("ENABLE_NEWS_ANALYZER"), True),
        enable_competitor_intelligence=parse_bool(os.getenv("ENABLE_COMPETITOR_INTELLIGENCE"), True),
        
        # MCP Tool Rate Limits
        google_trends_rate_limit=parse_int(os.getenv("GOOGLE_TRENDS_RATE_LIMIT")) or 100,
        social_media_rate_limit=parse_int(os.getenv("SOCIAL_MEDIA_RATE_LIMIT")) or 200,
        news_analyzer_rate_limit=parse_int(os.getenv("NEWS_ANALYZER_RATE_LIMIT")) or 150,
        
        # External APIs Configuration
        etsy_api_key=os.getenv("ETSY_API_KEY"),
        printify_base_url=os.getenv("PRINTIFY_BASE_URL", "https://api.printify.com/v1"),
        printify_rate_limit=parse_float(os.getenv("PRINTIFY_RATE_LIMIT"), 0.5),
        printify_retry_attempts=parse_int(os.getenv("PRINTIFY_RETRY_ATTEMPTS"), 3),
        etsy_base_url=os.getenv("ETSY_BASE_URL", "https://openapi.etsy.com/v3"),
        etsy_rate_limit=parse_float(os.getenv("ETSY_RATE_LIMIT"), 1.0),
        etsy_retry_attempts=parse_int(os.getenv("ETSY_RETRY_ATTEMPTS"), 3),
        
        # Google Workspace Integration
        google_sheets_tracking_id=os.getenv("GOOGLE_SHEETS_TRACKING_ID"),
        google_drive_root_folder_id=os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID"),
        sheets_update_frequency=os.getenv("SHEETS_UPDATE_FREQUENCY", "real_time"),
        
        # Performance Monitoring
        enable_performance_monitoring=parse_bool(os.getenv("ENABLE_PERFORMANCE_MONITORING"), True),
        enable_cloud_monitoring=parse_bool(os.getenv("ENABLE_CLOUD_MONITORING"), True),
        enable_cloud_logging=parse_bool(os.getenv("ENABLE_CLOUD_LOGGING"), True),
        enable_cloud_trace=parse_bool(os.getenv("ENABLE_CLOUD_TRACE"), True),
        
        # Caching
        enable_redis_caching=parse_bool(os.getenv("ENABLE_REDIS_CACHING"), True),
        cache_ttl_trend_data=parse_int(os.getenv("CACHE_TTL_TREND_DATA")) or 3600,
        cache_ttl_printify_catalog=parse_int(os.getenv("CACHE_TTL_PRINTIFY_CATALOG")) or 86400,
        cache_ttl_api_responses=parse_int(os.getenv("CACHE_TTL_API_RESPONSES")) or 300,
    )
    # In dry-run mode, allow missing Printify credentials
    if cfg.dry_run and (not api_token or not shop_id):
        cfg.printify_api_token = ""
        cfg.printify_shop_id = ""
    elif not api_token or not shop_id:
        raise RuntimeError("PRINTIFY_API_TOKEN and PRINTIFY_SHOP_ID must be set (see .env.example)")
    return cfg
