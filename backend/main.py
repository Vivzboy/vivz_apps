"""
Cape Town Property Discovery Platform - FastAPI Backend with MongoDB
Main application file
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from beanie import PydanticObjectId  # Instead of: from bson import ObjectId

# Local imports
from database.database import init_database, close_database, check_database_health, create_indexes
from models.property import (
    Property, PropertyCreate, PropertyUpdate, PropertyResponse, PropertyStatus,
    Comment, CommentCreate, CommentResponse,
    convert_scraper_output_to_property
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Cape Town Property Discovery API",
    description="Backend API for the property discovery platform with MongoDB",
    version="2.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    await init_database()
    await create_indexes()
    logger.info("🚀 Cape Town Property API with MongoDB started successfully!")

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await close_database()
    logger.info("👋 Application shutdown complete")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check API and database health"""
    db_health = await check_database_health()
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "database": db_health
    }

# ============================================================================
# PROPERTY ENDPOINTS
# ============================================================================

@app.get("/api/properties", response_model=List[PropertyResponse])
async def get_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    area: Optional[str] = Query(None),
    status: Optional[PropertyStatus] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    bedrooms: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Get properties with filtering and pagination
    This endpoint powers your React frontend feed
    """
    try:
        # Build MongoDB query
        query_conditions = {}
        
        if area:
            query_conditions["area"] = {"$regex": area, "$options": "i"}
        
        if status:
            query_conditions["status"] = status
        
        if min_price or max_price:
            price_conditions = {}
            if min_price:
                price_conditions["$gte"] = min_price
            if max_price:
                price_conditions["$lte"] = max_price
            query_conditions["price"] = price_conditions
        
        if bedrooms:
            query_conditions["bedrooms"] = bedrooms
        
        # For search, use MongoDB text search if available, otherwise regex
        if search:
            try:
                # Try text search first (requires text index)
                query_conditions["$text"] = {"$search": search}
            except:
                # Fallback to regex search
                search_regex = {"$regex": search, "$options": "i"}
                query_conditions["$or"] = [
                    {"title": search_regex},
                    {"area": search_regex},
                    {"neighborhood_vibe": search_regex}
                ]
        
        # Execute query with MongoDB
        if query_conditions:
            properties = await Property.find(query_conditions).skip(skip).limit(limit).sort(-Property.scraped_at).to_list()
        else:
            properties = await Property.find_all().skip(skip).limit(limit).sort(-Property.scraped_at).to_list()
        
        # Convert to response models
        return [PropertyResponse.from_property(prop) for prop in properties]
        
    except Exception as e:
        logger.error(f"Error getting properties: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get properties: {str(e)}")

@app.get("/api/properties/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: str):
    """Get a specific property by ID"""
    try:
        property_obj = await Property.get(PydanticObjectId(property_id))
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")
        
        return PropertyResponse.from_property(property_obj)
    except Exception as e:
        logger.error(f"Error getting property {property_id}: {e}")
        raise HTTPException(status_code=404, detail="Property not found")

@app.post("/api/properties", response_model=PropertyResponse)
async def create_property(property_data: PropertyCreate):
    """
    Create a new property
    Used by your scraper to add new properties
    """
    try:
        # Convert Pydantic model to Property document
        property_dict = property_data.dict(exclude_unset=True)
        property_obj = Property(**property_dict)
        
        # Save to MongoDB
        await property_obj.insert()
        
        logger.info(f"✅ Created property: {property_obj.title} in {property_obj.area}")
        return PropertyResponse.from_property(property_obj)
        
    except Exception as e:
        logger.error(f"Error creating property: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create property: {str(e)}")

@app.put("/api/properties/{property_id}", response_model=PropertyResponse)
async def update_property(property_id: str, property_update: PropertyUpdate):
    """Update property details"""
    try:
        property_obj = await Property.get(PydanticObjectId(property_id))
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Update fields
        update_data = property_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(property_obj, field, value)
        
        await property_obj.save()
        
        return PropertyResponse.from_property(property_obj)
        
    except Exception as e:
        logger.error(f"Error updating property {property_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update property: {str(e)}")

# ============================================================================
# SOCIAL FEATURES ENDPOINTS
# ============================================================================

@app.post("/api/properties/{property_id}/view")
async def track_property_view(property_id: str):
    """Track when a property is viewed (for analytics)"""
    try:
        property_obj = await Property.get(PydanticObjectId(property_id))
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")
        
        property_obj.views += 1
        await property_obj.save()
        
        return {"message": "View tracked", "total_views": property_obj.views}
        
    except Exception as e:
        logger.error(f"Error tracking view for property {property_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to track view")

@app.post("/api/properties/{property_id}/like")
async def toggle_property_like(property_id: str):
    """Toggle like on a property"""
    try:
        property_obj = await Property.get(PydanticObjectId(property_id))
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Simple like increment (in real app, you'd track user-specific likes)
        property_obj.likes += 1
        await property_obj.save()
        
        return {"message": "Like added", "total_likes": property_obj.likes}
        
    except Exception as e:
        logger.error(f"Error liking property {property_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to like property")

@app.get("/api/properties/{property_id}/comments", response_model=List[CommentResponse])
async def get_property_comments(property_id: str):
    """Get all comments for a property"""
    try:
        comments = await Comment.find(Comment.property_id == PydanticObjectId(property_id)).sort(-Comment.created_at).to_list()
        return [CommentResponse.from_comment(comment) for comment in comments]
        
    except Exception as e:
        logger.error(f"Error getting comments for property {property_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comments")

@app.post("/api/properties/{property_id}/comments", response_model=CommentResponse)
async def add_property_comment(property_id: str, comment_data: CommentCreate):
    """Add a comment to a property"""
    try:
        # Verify property exists
        property_obj = await Property.get(PydanticObjectId(property_id))
        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Create comment
        comment = Comment(
            property_id=PydanticObjectId(property_id),
            user_name=comment_data.user_name,
            user_avatar=comment_data.user_avatar,
            text=comment_data.text
        )
        
        await comment.insert()
        
        return CommentResponse.from_comment(comment)
        
    except Exception as e:
        logger.error(f"Error adding comment to property {property_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to add comment")

@app.post("/api/comments/{comment_id}/like")
async def like_comment(comment_id: str):
    """Like a comment"""
    try:
        comment = await Comment.get(PydanticObjectId(comment_id))
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        comment.likes += 1
        await comment.save()
        
        return {"message": "Comment liked", "total_likes": comment.likes}
        
    except Exception as e:
        logger.error(f"Error liking comment {comment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to like comment")

# ============================================================================
# SCRAPER INTEGRATION ENDPOINTS
# ============================================================================

@app.post("/api/scraper/import")
async def import_scraper_data(
    scraped_properties: List[dict], 
    background_tasks: BackgroundTasks
):
    """
    Import data from your Property24 scraper
    
    Expected format:
    [
        {
            "title": "2 Bedroom Apartment",
            "area": "Sea Point",
            "price": 1200000,
            "bedrooms": 2,
            "bathrooms": 2,
            "size_sqm": 85,
            "type": "Apartment",
            "url": "https://property24.com/...",
            "selector_used": "div.listing_tile"
        },
        ...
    ]
    """
    
    processed_count = 0
    error_count = 0
    
    for scraper_data in scraped_properties:
        try:
            # Convert scraper format to our PropertyCreate model
            property_create = convert_scraper_output_to_property(scraper_data)
            
            # Check if property already exists (by URL)
            existing = None
            if property_create.url:
                existing = await Property.find_one(Property.url == property_create.url)
            
            if not existing:
                # Create new property
                property_dict = property_create.dict(exclude_unset=True)
                property_obj = Property(**property_dict)
                await property_obj.insert()
                processed_count += 1
            else:
                # Update existing property price/details if changed
                if existing.price != property_create.price:
                    existing.price = property_create.price
                    existing.scraped_at = datetime.now()
                    await existing.save()
                
        except Exception as e:
            logger.error(f"Error processing property: {e}")
            error_count += 1
            continue
    
    logger.info(f"✅ Imported {processed_count} properties, {error_count} errors")
    
    total_properties = await Property.count()
    
    return {
        "message": "Import completed",
        "processed": processed_count,
        "errors": error_count,
        "total_properties": total_properties
    }

@app.get("/api/scraper/stats")
async def get_scraper_stats():
    """Get scraping statistics"""
    try:
        total_properties = await Property.count()
        
        # Properties by area (aggregation)
        area_pipeline = [
            {"$group": {"_id": "$area", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        area_stats = await Property.aggregate(area_pipeline).to_list(length=None)
        
        # Recent scraping activity
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_scrapes = await Property.find(Property.scraped_at >= recent_cutoff).count()
        
        # Status distribution
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_stats = await Property.aggregate(status_pipeline).to_list(length=None)
        
        # Latest scrape
        latest_property = await Property.find().sort(-Property.scraped_at).first_or_none()
        
        return {
            "total_properties": total_properties,
            "recent_scrapes_7d": recent_scrapes,
            "properties_by_area": {stat["_id"]: stat["count"] for stat in area_stats},
            "properties_by_status": {stat["_id"]: stat["count"] for stat in status_stats},
            "last_scrape": latest_property.scraped_at if latest_property else None
        }
        
    except Exception as e:
        logger.error(f"Error getting scraper stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stats")

# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/analytics/market")
async def get_market_analytics(area: Optional[str] = None):
    """
    Get market analytics - perfect for your actuarial background!
    """
    try:
        # Build query
        query = {}
        if area:
            query["area"] = {"$regex": area, "$options": "i"}
        
        properties = await Property.find(query).to_list()
        
        if not properties:
            return {"message": "No data available"}
        
        # Calculate statistics
        prices = [p.price for p in properties if p.price]
        price_per_sqm = [p.price_per_sqm for p in properties if p.price_per_sqm]
        
        analytics = {
            "total_properties": len(properties),
            "price_stats": {},
            "price_per_sqm_stats": {},
            "property_types": {},
            "bedroom_distribution": {}
        }
        
        # Price statistics
        if prices:
            sorted_prices = sorted(prices)
            analytics["price_stats"] = {
                "median": sorted_prices[len(sorted_prices)//2],
                "mean": sum(prices) / len(prices),
                "min": min(prices),
                "max": max(prices)
            }
        
        # Price per sqm statistics
        if price_per_sqm:
            sorted_psqm = sorted(price_per_sqm)
            analytics["price_per_sqm_stats"] = {
                "median": sorted_psqm[len(sorted_psqm)//2],
                "mean": sum(price_per_sqm) / len(price_per_sqm)
            }
        
        # Property type distribution
        for prop in properties:
            prop_type = prop.property_type
            analytics["property_types"][prop_type] = analytics["property_types"].get(prop_type, 0) + 1
        
        # Bedroom distribution
        for prop in properties:
            bedrooms = prop.bedrooms or 0
            analytics["bedroom_distribution"][bedrooms] = analytics["bedroom_distribution"].get(bedrooms, 0) + 1
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting market analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics")

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/api/areas")
async def get_areas():
    """Get all available areas with property counts"""
    try:
        pipeline = [
            {"$group": {"_id": "$area", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        areas = await Property.aggregate(pipeline).to_list(length=None)
        return [{"area": area["_id"], "property_count": area["count"]} for area in areas]
        
    except Exception as e:
        logger.error(f"Error getting areas: {e}")
        raise HTTPException(status_code=500, detail="Failed to get areas")
    
@app.delete("/api/properties/cleanup")
async def cleanup_database(
    area: Optional[str] = Query(None),
    older_than_days: Optional[int] = Query(None)
):
    """
    Clean up properties from database
    
    Query params:
    - area: Clean only specific area
    - older_than_days: Clean properties older than X days
    """
    try:
        if area:
            # Delete by area
            result = await Property.find(Property.area == area).delete()
            return {"message": f"Deleted properties from {area}", "deleted": result.deleted_count}
        
        elif older_than_days:
            # Delete old properties
            cutoff = datetime.now() - timedelta(days=older_than_days)
            result = await Property.find(Property.scraped_at < cutoff).delete()
            return {"message": f"Deleted properties older than {older_than_days} days", 
                    "deleted": result.deleted_count}
        
        else:
            # Delete ALL (dangerous!)
            result = await Property.delete_all()
            await Comment.delete_all()  # Also clean comments
            return {"message": "Deleted ALL properties and comments", 
                    "deleted": result.deleted_count}
                    
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)