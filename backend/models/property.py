"""
Property data models for the Cape Town Property Discovery Platform
MongoDB/Beanie version - Fixed Indexed Enum issue
"""

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional, List

class PropertyStatus(str, Enum):
    AVAILABLE = "available"
    UNDER_OFFER = "under_offer"
    SOLD = "sold"
    OFF_MARKET = "off_market"

class PropertyType(str, Enum):
    APARTMENT = "Apartment"
    HOUSE = "House"
    TOWNHOUSE = "Townhouse"
    FLAT = "Flat"
    PROPERTY = "Property"

# MongoDB Document Models using Beanie
class Property(Document):
    """
    Main Property document for MongoDB
    Beanie automatically handles _id as ObjectId
    """
    
    # Core property data (from your scraper)
    title: str = Field(..., description="Property title")
    area: Indexed(str) = Field(..., description="Property area/location")
    price: Optional[int] = Field(None, description="Price in Rands")
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqm: Optional[int] = None
    property_type: str = Field(default="Property", description="Type of property")
    
    # URLs and external data
    url: Optional[str] = None
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    
    # Property details
    highlights: List[str] = Field(default_factory=list, description="Property highlights")
    neighborhood_vibe: Optional[str] = None
    
    # Status tracking - Fixed: using str type with index in Settings
    status: str = Field(default=PropertyStatus.AVAILABLE.value)
    listed_date: Optional[datetime] = None
    sold_date: Optional[datetime] = None
    withdrawn_date: Optional[datetime] = None
    sold_price: Optional[int] = None
    
    # Engagement metrics (for social features)
    views: int = Field(default=0)
    likes: int = Field(default=0)
    
    # Scraper metadata
    scraped_at: Indexed(datetime) = Field(default_factory=datetime.now)
    selector_used: Optional[str] = None  # Which scraper selector worked
    
    # MongoDB collection settings
    class Settings:
        name = "properties"  # Collection name
        indexes = [
            [("area", 1), ("status", 1)],  # Compound index for filtering
            [("status", 1)],  # Single index for status
            [("price", 1)],
            [("scraped_at", -1)],  # For recent properties
            [("url", 1)],  # For duplicate detection
        ]
    
    # Computed properties
    @property
    def price_per_sqm(self) -> Optional[float]:
        if self.price and self.size_sqm and self.size_sqm > 0:
            return round(self.price / self.size_sqm, 2)
        return None
    
    @property
    def days_on_market(self) -> Optional[int]:
        if self.listed_date:
            end_date = self.sold_date or self.withdrawn_date or datetime.now()
            return (end_date - self.listed_date).days
        return None
    
    @property
    def is_deal(self) -> bool:
        """Simple logic to identify deals - you can enhance this"""
        if not self.price_per_sqm:
            return False
        
        # Example: Properties under R15k per sqm in prime areas
        prime_areas = ["clifton", "camps-bay", "sea-point"]
        if self.area.lower().replace(" ", "-") in prime_areas:
            return self.price_per_sqm < 15000
        
        # General deal threshold
        return self.price_per_sqm < 12000

class Comment(Document):
    """Comments on properties"""
    
    property_id: PydanticObjectId = Field(..., description="Reference to Property")
    user_name: str = Field(..., max_length=100)
    user_avatar: str = Field(default="👤", max_length=10)
    text: str = Field(..., description="Comment text")
    likes: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "comments"
        indexes = [
            [("property_id", 1), ("created_at", -1)],  # Comments by property, newest first
        ]

# Pydantic models for API requests/responses (no changes needed from SQLAlchemy version)
class PropertyBase(BaseModel):
    title: str
    area: str
    price: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqm: Optional[int] = None
    property_type: str = "Property"
    url: Optional[str] = None
    images: Optional[List[str]] = []
    highlights: Optional[List[str]] = []
    neighborhood_vibe: Optional[str] = None
    status: PropertyStatus = PropertyStatus.AVAILABLE

class PropertyCreate(PropertyBase):
    """For creating new properties from scraper"""
    selector_used: Optional[str] = None
    listed_date: Optional[datetime] = None

class PropertyUpdate(BaseModel):
    """For updating property status, prices, etc."""
    status: Optional[PropertyStatus] = None
    sold_price: Optional[int] = None
    sold_date: Optional[datetime] = None
    withdrawn_date: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None

class PropertyResponse(BaseModel):
    """Full property response for frontend"""
    id: str = Field(alias="_id")  # MongoDB ObjectId as string
    title: str
    area: str
    price: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    size_sqm: Optional[int] = None
    property_type: str
    url: Optional[str] = None
    images: List[str] = []
    highlights: List[str] = []
    neighborhood_vibe: Optional[str] = None
    status: PropertyStatus
    views: int
    likes: int
    scraped_at: datetime
    
    # Computed fields
    price_per_sqm: Optional[float] = None
    days_on_market: Optional[int] = None
    deal: bool = False
    
    class Config:
        populate_by_name = True  # Allow both _id and id
        
    @classmethod
    def from_property(cls, property_doc: Property):
        """Convert Property document to response model"""
        # Convert status string back to enum
        status_enum = PropertyStatus(property_doc.status) if isinstance(property_doc.status, str) else property_doc.status
        
        return cls(
            id=str(property_doc.id),
            title=property_doc.title,
            area=property_doc.area,
            price=property_doc.price,
            bedrooms=property_doc.bedrooms,
            bathrooms=property_doc.bathrooms,
            size_sqm=property_doc.size_sqm,
            property_type=property_doc.property_type,
            url=property_doc.url,
            images=property_doc.images,
            highlights=property_doc.highlights,
            neighborhood_vibe=property_doc.neighborhood_vibe,
            status=status_enum,
            views=property_doc.views,
            likes=property_doc.likes,
            scraped_at=property_doc.scraped_at,
            price_per_sqm=property_doc.price_per_sqm,
            days_on_market=property_doc.days_on_market,
            deal=property_doc.is_deal
        )

class CommentCreate(BaseModel):
    user_name: str
    user_avatar: str = "👤"
    text: str

class CommentResponse(BaseModel):
    id: str = Field(alias="_id")
    property_id: str
    user_name: str
    user_avatar: str
    text: str
    likes: int
    created_at: datetime
    
    class Config:
        populate_by_name = True
        
    @classmethod
    def from_comment(cls, comment_doc: Comment):
        """Convert Comment document to response model"""
        return cls(
            id=str(comment_doc.id),
            property_id=str(comment_doc.property_id),
            user_name=comment_doc.user_name,
            user_avatar=comment_doc.user_avatar,
            text=comment_doc.text,
            likes=comment_doc.likes,
            created_at=comment_doc.created_at
        )


def convert_scraper_output_to_property(scraper_data: dict) -> PropertyCreate:
    """
    Convert your existing scraper output to our Property model
    
    Expected scraper_data format (from your existing scraper):
    {
        "title": "2 Bedroom Apartment",
        "area": "Sea Point", 
        "price": 1200000,
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqm": 85,
        "type": "Apartment",
        "url": "https://property24.com/...",
        "selector_used": "div.listing_tile",
        "images": ["https://...", "https://..."],  # NOW EXPECTING IMAGES!
        "highlights": ["Pool", "Security"]
    }
    """
    
    # Map your scraper keys to our model
    property_data = PropertyCreate(
        title=scraper_data.get("title", "Property"),
        area=scraper_data.get("area", "Unknown"),
        price=scraper_data.get("price"),
        bedrooms=scraper_data.get("bedrooms"),
        bathrooms=scraper_data.get("bathrooms"),
        size_sqm=scraper_data.get("size_sqm"),
        property_type=scraper_data.get("type", "Property"),
        url=scraper_data.get("url"),
        selector_used=scraper_data.get("selector_used"),
        
        # ✅ ADD THIS LINE - THIS IS THE FIX!
        images=scraper_data.get("images", []),
        
        # Also get highlights from scraper if available
        highlights=scraper_data.get("highlights", generate_area_highlights(scraper_data.get("area", ""))),
        neighborhood_vibe=scraper_data.get("neighborhood_vibe", generate_neighborhood_vibe(scraper_data.get("area", ""))),
        listed_date=datetime.now()
    )
    
    return property_data

def generate_area_highlights(area: str) -> List[str]:
    """Generate highlights based on Cape Town area"""
    area_lower = area.lower().replace(" ", "-")
    
    highlights_map = {
        "sea-point": ["2-min walk to beach", "Great coffee nearby", "Mountain views"],
        "camps-bay": ["Ocean views", "Private terrace", "Designer kitchen"],
        "green-point": ["Walking to V&A", "Modern finishes", "Gym in building"],
        "clifton": ["Beach access", "Luxury finishes", "Concierge service"],
        "fresnaye": ["Large garden", "Sea glimpses", "Double garage"],
        "de-waterkant": ["Industrial chic", "High ceilings", "Trendy location"],
        "gardens": ["City bowl living", "Cultural attractions", "Easy CBD access"],
        "oranjezicht": ["Quiet residential", "Mountain proximity", "Historic charm"],
        "tamboerskloof": ["Trendy cafes", "Art galleries", "City views"],
        "vredehoek": ["Peaceful setting", "Nature access", "Stunning views"]
    }
    
    return highlights_map.get(area_lower, ["Great location", "Well-positioned", "Good access"])

def generate_neighborhood_vibe(area: str) -> str:
    """Generate neighborhood descriptions based on area"""
    area_lower = area.lower().replace(" ", "-")
    
    vibes_map = {
        "sea-point": "Vibrant beachfront living with excellent restaurants",
        "camps-bay": "Exclusive beach paradise with stunning sunsets", 
        "green-point": "Urban sophistication meets waterfront convenience",
        "clifton": "Ultimate luxury beachfront lifestyle",
        "fresnaye": "Peaceful residential area with stunning city views",
        "de-waterkant": "Hip, artistic quarter with great restaurants",
        "gardens": "Cultural heart of Cape Town with historic charm",
        "oranjezicht": "Quiet residential haven below Table Mountain",
        "tamboerskloof": "Trendy hillside community with artistic flair",
        "vredehoek": "Tranquil mountain setting with panoramic views"
    }
    
    return vibes_map.get(area_lower, "Desirable Cape Town location")
