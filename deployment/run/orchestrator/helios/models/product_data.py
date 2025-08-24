"""Product data models for Helios Autonomous Store"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class ProductStatus(Enum):
    """Product status enumeration"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    ERROR = "error"


class ProductType(Enum):
    """Product type enumeration"""
    T_SHIRT = "t_shirt"
    HOODIE = "hoodie"
    MUG = "mug"
    POSTER = "poster"
    STICKER = "sticker"
    PHONE_CASE = "phone_case"
    NOTEBOOK = "notebook"
    BAG = "bag"
    CAP = "cap"
    OTHER = "other"


@dataclass
class PrintArea:
    """Print area specification for products"""
    name: str
    x: float
    y: float
    width: float
    height: float
    unit: str = "mm"
    required: bool = True
    max_colors: int = 1
    description: Optional[str] = None


@dataclass
class ProductVariant:
    """Product variant information"""
    variant_id: str
    title: str
    price: float
    currency: str = "USD"
    colors: List[str] = field(default_factory=list)
    sizes: List[str] = field(default_factory=list)
    print_areas: List[PrintArea] = field(default_factory=list)
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    is_available: bool = True
    inventory_quantity: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProductData:
    """Complete product data structure"""
    product_id: str
    title: str
    description: str
    product_type: ProductType
    blueprint_id: int
    print_provider_id: int
    variants: List[ProductVariant]
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    status: ProductStatus = ProductStatus.DRAFT
    is_published: bool = False
    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Printify specific fields
    printify_product_id: Optional[str] = None
    printify_shop_id: Optional[str] = None
    etsy_listing_id: Optional[str] = None
    
    # Performance metrics
    views: int = 0
    sales: int = 0
    revenue: float = 0.0
    profit_margin: float = 0.0
    
    # Metadata
    trend_source: Optional[str] = None
    audience_target: Optional[str] = None
    marketing_copy: Optional[str] = None
    design_prompt: Optional[str] = None
    generated_image_url: Optional[str] = None
    
    # Quality metrics
    quality_score: float = 0.0
    compliance_status: str = "pending"
    safety_rating: float = 0.0
    
    def get_base_price(self) -> float:
        """Get the base price from variants"""
        if not self.variants:
            return 0.0
        return min(variant.price for variant in self.variants)
    
    def get_total_variants(self) -> int:
        """Get total number of variants"""
        return len(self.variants)
    
    def is_ready_for_publication(self) -> bool:
        """Check if product is ready for publication"""
        return (
            self.status == ProductStatus.DRAFT and
            self.variants and
            self.generated_image_url and
            self.marketing_copy and
            self.quality_score >= 7.0
        )
