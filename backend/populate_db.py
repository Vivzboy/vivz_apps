"""
Enhanced populate script with optional database cleanup
"""

import sys
import os
import requests
import time
import logging
import json
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.scraper import Property24Scraper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_database():
    """
    Clean the database by removing all properties
    WARNING: This deletes ALL property data!
    """
    logger.warning("⚠️  Cleaning database - this will DELETE all properties!")
    
    try:
        # First, get count of existing properties
        response = requests.get("http://localhost:8000/api/properties?limit=1000")
        if response.status_code == 200:
            existing_count = len(response.json())
            logger.info(f"📊 Found {existing_count} existing properties")
        
        # Since we don't have a delete endpoint, we need to add one
        # For now, we'll note this limitation
        logger.warning("❌ No delete endpoint available in current API")
        logger.info("💡 To clean database manually:")
        logger.info("   1. Connect to MongoDB")
        logger.info("   2. Run: db.properties.deleteMany({})")
        logger.info("   3. Run: db.comments.deleteMany({})")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking database: {e}")
        return False

def clean_area_properties(area: str):
    """
    Clean properties from a specific area only
    More targeted approach than full cleanup
    """
    logger.info(f"🧹 Cleaning properties from {area}...")
    
    # This would require an API endpoint like:
    # DELETE /api/properties?area=sea-point
    # Currently not implemented
    
    logger.warning("❌ Area-specific cleanup not available in current API")
    return False

def populate_database_smart(extract_images=True, max_pages=2, clean_first=False, 
                          clean_areas=None, update_existing=True):
    """
    Smart database population with various options
    
    Args:
        extract_images: Whether to extract images
        max_pages: Max pages per area to scrape
        clean_first: Whether to clean entire database first
        clean_areas: List of specific areas to clean before scraping
        update_existing: Whether to update existing properties
    """
    
    # 1. Check if backend is running
    logger.info("🔍 Checking if backend is running...")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code != 200:
            raise Exception("Backend not healthy")
        
        health = response.json()
        db_status = health.get('database', {})
        logger.info("✅ Backend is running!")
        logger.info(f"📊 Current database: {db_status.get('total_properties', 'unknown')} properties")
        
    except:
        logger.error("❌ Backend is not running! Please start it first:")
        logger.error("   cd backend")
        logger.error("   uvicorn main:app --reload")
        return False
    
    # 2. Optional cleanup
    if clean_first:
        logger.warning("\n⚠️  CLEANUP REQUESTED - This will delete ALL properties!")
        response = input("Are you sure? Type 'yes' to confirm: ")
        if response.lower() == 'yes':
            clean_database()
        else:
            logger.info("❌ Cleanup cancelled")
    
    # 3. Get current property stats before scraping
    try:
        response = requests.get("http://localhost:8000/api/scraper/stats")
        if response.status_code == 200:
            stats = response.json()
            logger.info(f"\n📊 Before scraping:")
            logger.info(f"   Total properties: {stats.get('total_properties', 0)}")
            logger.info(f"   By area: {stats.get('properties_by_area', {})}")
    except:
        pass
    
    # 4. Initialize scraper
    logger.info("\n🚀 Initializing Enhanced Property24 scraper...")
    scraper = Property24Scraper(delay_between_requests=1.0)
    
    # 5. Scrape areas
    areas_to_scrape = ["sea-point", "gardens", "green-point"]
    all_properties = []
    
    for area in areas_to_scrape:
        logger.info(f"\n🏠 Scraping {area} (max {max_pages} pages)...")
        
        try:
            properties = scraper.scrape_area(
                area, 
                max_pages=max_pages,
                extract_images=extract_images
            )
            
            # Statistics
            with_images = sum(1 for p in properties if p.get('images'))
            logger.info(f"   Found {len(properties)} properties ({with_images} with images)")
            
            all_properties.extend(properties)
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"   Error scraping {area}: {e}")
    
    if not all_properties:
        logger.error("❌ No properties found!")
        return False
    
    # 6. Transform and prepare for import
    logger.info(f"\n🔄 Transforming {len(all_properties)} properties...")
    
    # Group by area for better logging
    by_area = {}
    api_properties = []
    
    for prop in all_properties:
        area = prop.get("area", "Unknown")
        if area not in by_area:
            by_area[area] = {"total": 0, "with_images": 0}
        
        by_area[area]["total"] += 1
        if prop.get("images"):
            by_area[area]["with_images"] += 1
        
        # Transform to API format
        api_prop = {
            "title": prop.get("title", "Property"),
            "area": area,
            "price": prop.get("price"),
            "bedrooms": prop.get("bedrooms"),
            "bathrooms": prop.get("bathrooms"),
            "size_sqm": prop.get("size_sqm"),
            "property_type": prop.get("type", "Property"),
            "url": prop.get("url"),
            "selector_used": prop.get("selector_used"),
            "images": prop.get("images", []),
            "highlights": prop.get("highlights", []),
            "neighborhood_vibe": prop.get("neighborhood_vibe"),
        }
        
        api_prop = {k: v for k, v in api_prop.items() if v is not None}
        api_properties.append(api_prop)
    
    # Show what we're about to import
    logger.info("\n📋 Ready to import:")
    for area, stats in by_area.items():
        logger.info(f"   {area}: {stats['total']} properties ({stats['with_images']} with images)")
    
    # 7. Import to backend
    logger.info("\n📤 Importing to backend...")
    try:
        response = requests.post(
            "http://localhost:8000/api/scraper/import",
            json=api_properties,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Import complete!")
            logger.info(f"   Processed: {result['processed']} properties")
            logger.info(f"   Errors: {result.get('errors', 0)}")
            logger.info(f"   Total in DB: {result['total_properties']}")
            
            # Calculate what happened
            new_properties = result['processed']
            updated_properties = len(api_properties) - new_properties
            logger.info(f"\n📊 Summary:")
            logger.info(f"   New properties added: {new_properties}")
            logger.info(f"   Existing properties updated: {updated_properties}")
            
        else:
            logger.error(f"❌ Import failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Import error: {e}")
        return False
    
    # 8. Final stats
    try:
        response = requests.get("http://localhost:8000/api/scraper/stats")
        if response.status_code == 200:
            stats = response.json()
            logger.info(f"\n📊 After scraping:")
            logger.info(f"   Total properties: {stats.get('total_properties', 0)}")
            logger.info(f"   Recent scrapes (7d): {stats.get('recent_scrapes_7d', 0)}")
            logger.info(f"   Last scrape: {stats.get('last_scrape', 'unknown')}")
    except:
        pass
    
    logger.info("\n🎉 Database population complete!")
    logger.info("📱 Visit http://localhost:5173 to see your properties!")
    
    return True

def show_database_info():
    """Show detailed database information"""
    logger.info("📊 Database Information")
    
    try:
        # Get stats
        response = requests.get("http://localhost:8000/api/scraper/stats")
        if response.status_code == 200:
            stats = response.json()
            
            logger.info(f"\n📈 Overview:")
            logger.info(f"   Total properties: {stats.get('total_properties', 0)}")
            logger.info(f"   Recent activity (7d): {stats.get('recent_scrapes_7d', 0)} properties")
            
            logger.info(f"\n📍 By Area:")
            for area, count in stats.get('properties_by_area', {}).items():
                logger.info(f"   {area}: {count} properties")
            
            logger.info(f"\n🏷️ By Status:")
            for status, count in stats.get('properties_by_status', {}).items():
                logger.info(f"   {status}: {count} properties")
    
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Smart database population with options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python populate_database.py                    # Normal population (adds to existing)
  python populate_database.py --clean           # Clean database first (DELETES ALL!)
  python populate_database.py --no-images       # Faster scraping without images
  python populate_database.py --pages 5         # Scrape more pages
  python populate_database.py --info            # Show database statistics
        """
    )
    
    parser.add_argument("--clean", action="store_true", 
                       help="⚠️  Clean database before populating (DELETES ALL DATA!)")
    parser.add_argument("--no-images", action="store_true",
                       help="Skip image extraction (faster)")
    parser.add_argument("--pages", type=int, default=2,
                       help="Max pages per area to scrape (default: 2)")
    parser.add_argument("--info", action="store_true",
                       help="Show database information and exit")
    
    args = parser.parse_args()
    
    if args.info:
        show_database_info()
    else:
        populate_database_smart(
            extract_images=not args.no_images,
            max_pages=args.pages,
            clean_first=args.clean
        )