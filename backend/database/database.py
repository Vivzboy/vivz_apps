"""
MongoDB database configuration for Cape Town Property Discovery Platform
Using Beanie ODM with Motor (async MongoDB driver)
"""

import motor.motor_asyncio
from beanie import init_beanie
from models.property import Property, Comment
import os
from typing import List
import asyncio
import logging
from beanie import PydanticObjectId
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# MongoDB connection settings
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27018")
DATABASE_NAME = os.getenv("DATABASE_NAME", "cape_town_properties")

# Global database client
client = None
database = None

async def init_database():
    """
    Initialize MongoDB connection and Beanie ODM
    Call this when starting the application
    """
    global client, database
    
    try:
        # Create Motor client
        client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
        database = client[DATABASE_NAME]
        
        # Test connection
        await client.admin.command('ping')
        logger.info(f"✅ Connected to MongoDB at {MONGODB_URL}")
        
        # Initialize Beanie with the Product and Comment documents
        await init_beanie(
            database=database,
            document_models=[Property, Comment]
        )
        
        logger.info("✅ Beanie ODM initialized successfully!")
        logger.info(f"📦 Database: {DATABASE_NAME}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise e

async def close_database():
    """Close database connection"""
    global client
    if client:
        client.close()
        logger.info("📪 MongoDB connection closed")

async def reset_database():
    """
    Drop and recreate collections - use with caution!
    """
    global database
    if database:
        # Drop collections
        await database.drop_collection("properties")
        await database.drop_collection("comments")
        
        # Reinitialize Beanie
        await init_beanie(
            database=database,
            document_models=[Property, Comment]
        )
        
        logger.info("🔄 Database reset complete!")

# Database utilities
class DatabaseUtils:
    """Utility functions for MongoDB operations"""
    
    @staticmethod
    async def get_property_count() -> int:
        """Get total number of properties"""
        return await Property.count()
    
    @staticmethod
    async def get_properties_by_area(area: str) -> List[Property]:
        """Get all properties in a specific area"""
        return await Property.find(Property.area == area).to_list()
    
    @staticmethod
    async def get_available_properties() -> List[Property]:
        """Get only available properties"""
        return await Property.find(Property.status == "available").to_list()
    
    @staticmethod
    async def bulk_insert_properties(properties_data: List[dict]) -> int:
        """
        Efficiently insert multiple properties
        Useful for bulk scraper imports
        """
        try:
            # Convert dicts to Property documents
            property_objects = []
            
            for prop_data in properties_data:
                # Check if property already exists by URL
                if prop_data.get("url"):
                    existing = await Property.find_one(Property.url == prop_data["url"])
                    if existing:
                        continue  # Skip duplicates
                
                # Create new property
                property_obj = Property(**prop_data)
                property_objects.append(property_obj)
            
            if property_objects:
                await Property.insert_many(property_objects)
                logger.info(f"✅ Inserted {len(property_objects)} new properties")
            
            return len(property_objects)
            
        except Exception as e:
            logger.error(f"❌ Bulk insert failed: {e}")
            raise e
    
    @staticmethod
    async def update_property_status(property_id: str, status: str, sold_price: int = None):
        """Update property status (sold, under offer, etc.)"""
        from datetime import datetime
        
        try:
            property_obj = await Property.get(PydanticObjectId(property_id))
            if property_obj:
                property_obj.status = status
                if status == "sold" and sold_price:
                    property_obj.sold_price = sold_price
                    property_obj.sold_date = datetime.now()
                await property_obj.save()
                return property_obj
        except Exception as e:
            logger.error(f"❌ Failed to update property status: {e}")
        
        return None
    
    @staticmethod
    async def search_properties(query: str, limit: int = 50) -> List[Property]:
        """Search properties by text"""
        # MongoDB text search (requires text index)
        return await Property.find(
            {"$text": {"$search": query}}
        ).limit(limit).to_list()
    
    @staticmethod
    async def get_recent_properties(days: int = 7, limit: int = 100) -> List[Property]:
        """Get recently scraped properties"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return await Property.find(
            Property.scraped_at >= cutoff_date
        ).limit(limit).sort(-Property.scraped_at).to_list()

# Database health check
async def check_database_health() -> dict:
    """
    Check if database is healthy and return stats
    """
    try:
        global client, database
        
        if not client or not database:
            return {"status": "unhealthy", "error": "No database connection"}
        
        # Test connection
        await client.admin.command('ping')
        
        # Get statistics
        property_count = await Property.count()
        comment_count = await Comment.count()
        
        # Get latest scraped property
        latest_property = await Property.find().sort(-Property.scraped_at).first_or_none()
        
        # Database size info
        stats = await database.command("dbStats")
        
        return {
            "status": "healthy",
            "total_properties": property_count,
            "total_comments": comment_count,
            "latest_scrape": latest_property.scraped_at if latest_property else None,
            "database_name": DATABASE_NAME,
            "database_size_mb": round(stats.get("dataSize", 0) / 1024 / 1024, 2),
            "collections": stats.get("collections", 0),
            "mongodb_version": (await client.server_info()).get("version", "unknown")
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Indexing utilities
async def create_indexes():
    """
    Create additional indexes for better performance
    Call this after database initialization
    """
    try:
        # Text search index for properties
        await database.properties.create_index([
            ("title", "text"),
            ("area", "text"), 
            ("neighborhood_vibe", "text"),
            ("highlights", "text")
        ])
        
        # Geospatial index (if you add coordinates later)
        # await database.properties.create_index([("location", "2dsphere")])
        
        logger.info("✅ Additional indexes created successfully!")
        
    except Exception as e:
        logger.error(f"⚠️  Index creation failed: {e}")

# Migration utilities (for future schema changes)
async def create_migration_backup():
    """Create a backup collection before running migrations"""
    from datetime import datetime
    
    try:
        backup_name = f"properties_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Copy collection
        pipeline = [{"$out": backup_name}]
        await database.properties.aggregate(pipeline).to_list(length=None)
        
        logger.info(f"📦 Database backup created: {backup_name}")
        return backup_name
        
    except Exception as e:
        logger.error(f"⚠️  Backup creation failed: {e}")
        return None

# Connection test function
async def test_connection():
    """Test MongoDB connection"""
    try:
        await init_database()
        health = await check_database_health()
        await close_database()
        return health
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# Command line testing
if __name__ == "__main__":
    async def main():
        print("🧪 Testing MongoDB connection...")
        result = await test_connection()
        print(f"Result: {result}")
    
    asyncio.run(main())
