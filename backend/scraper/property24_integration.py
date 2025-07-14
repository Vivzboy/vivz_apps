"""
Integration script to connect your Property24 scraper with images to the backend
This bridges your enhanced scraper with the FastAPI backend
"""

import requests
import json
from datetime import datetime
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyAPIClient:
    """Client to interact with your Property Discovery API"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """Check if the API is running"""
        try:
            response = self.session.get(f"{self.api_base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False
    
    def import_properties(self, properties: List[Dict]) -> Dict:
        """
        Import scraped properties to the backend
        
        Args:
            properties: List of property dictionaries from your scraper
            
        Returns:
            Import result with counts and status
        """
        try:
            response = self.session.post(
                f"{self.api_base_url}/api/scraper/import",
                json=properties,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to import properties: {e}")
            raise

def transform_scraper_output(scraper_property: Dict) -> Dict:
    """
    Transform your scraper output to match the API format
    Now includes image handling
    """
    
    # Transform to API format
    transformed = {
        "title": scraper_property.get("title", "Property"),
        "area": scraper_property.get("area", "Unknown"),
        "price": scraper_property.get("price"),
        "bedrooms": scraper_property.get("bedrooms"),
        "bathrooms": scraper_property.get("bathrooms"), 
        "size_sqm": scraper_property.get("size_sqm"),
        "property_type": scraper_property.get("type", "Property"),
        "url": scraper_property.get("url"),
        "neighborhood_vibe": scraper_property.get("neighborhood_vibe"),
        "selector_used": scraper_property.get("selector_used"),
        
        # Images - ensure it's a list
        "images": scraper_property.get("images", []),
        
        # Highlights from feature extraction
        "highlights": scraper_property.get("highlights", []),
    }
    
    # Validate images are proper URLs
    if transformed["images"]:
        valid_images = []
        for img in transformed["images"]:
            if isinstance(img, str) and (img.startswith("http://") or img.startswith("https://")):
                valid_images.append(img)
        transformed["images"] = valid_images[:5]  # Limit to 5 images
    
    # Remove None values
    return {k: v for k, v in transformed.items() if v is not None}

def run_scraper_and_import_with_images(areas: List[str] = None, max_pages: int = 5, 
                                       extract_images: bool = True, dry_run: bool = False):
    """
    Main function to run your enhanced scraper and import results to the backend
    
    Args:
        areas: List of areas to scrape
        max_pages: Maximum pages per area
        extract_images: Whether to extract images
        dry_run: If True, just prints data without sending to backend
    """
    
    # Import your enhanced scraper
    try:
        # Update this import path to match your project structure
        from scraper import Property24Scraper  
        logger.info("✅ Imported enhanced Property24Scraper")
    except ImportError:
        logger.error("❌ Could not import your scraper. Please update the import path.")
        return
    
    # Initialize API client (unless dry run)
    api_client = None
    if not dry_run:
        api_client = PropertyAPIClient()
        
        # Check if backend is running
        if not api_client.health_check():
            logger.error("❌ Backend API is not running. Please start it with: uvicorn main:app --reload")
            return
        
        logger.info("✅ Backend API is healthy")
    
    # Initialize your scraper
    scraper = Property24Scraper(delay_between_requests=1.0)
    
    # Default areas if none provided
    if not areas:
        areas = ["sea-point", "camps-bay", "green-point"]
    
    all_properties = []
    
    # Run scraper for each area
    for area in areas:
        logger.info(f"🔍 Scraping {area} with image extraction {'enabled' if extract_images else 'disabled'}...")
        
        try:
            # Use enhanced scraper with image extraction
            area_properties = scraper.scrape_area(
                area, 
                max_pages=max_pages, 
                extract_images=extract_images
            )
            
            logger.info(f"📊 Found {len(area_properties)} properties in {area}")
            
            # Log sample property with images
            if area_properties and area_properties[0].get('images'):
                sample = area_properties[0]
                logger.info(f"   Sample: {sample['title']} - {len(sample.get('images', []))} images")
            
            # Transform each property to API format
            transformed_properties = [transform_scraper_output(prop) for prop in area_properties]
            all_properties.extend(transformed_properties)
            
        except Exception as e:
            logger.error(f"❌ Error scraping {area}: {e}")
            continue
    
    # Show results
    logger.info(f"\n📊 Total properties scraped: {len(all_properties)}")
    
    # Count properties with images
    properties_with_images = sum(1 for p in all_properties if p.get('images'))
    logger.info(f"🖼️  Properties with images: {properties_with_images}/{len(all_properties)}")
    
    if dry_run:
        # Just save to file for inspection
        filename = f"scraped_properties_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(all_properties, f, indent=2)
        logger.info(f"💾 Dry run - saved to {filename}")
        
        # Show sample
        if all_properties:
            logger.info("\n📄 Sample property:")
            sample = all_properties[0]
            logger.info(f"   Title: {sample['title']}")
            logger.info(f"   Price: R{sample.get('price', 'N/A'):,}")
            logger.info(f"   Images: {len(sample.get('images', []))}")
            if sample.get('images'):
                logger.info(f"   First image: {sample['images'][0]}")
    else:
        # Import to backend
        if all_properties:
            logger.info(f"📤 Importing {len(all_properties)} properties to backend...")
            
            try:
                result = api_client.import_properties(all_properties)
                logger.info(f"✅ Import completed: {result}")
                
            except Exception as e:
                logger.error(f"❌ Import failed: {e}")

def test_single_property_with_images():
    """
    Test scraping a single property with detailed image extraction
    """
    from scraper import Property24Scraper
    
    scraper = Property24Scraper()
    
    # Scrape just one page of one area
    properties = scraper.scrape_area("sea-point", max_pages=1, extract_images=True)
    
    if properties:
        # Find a property with images
        for prop in properties:
            if prop.get('images'):
                logger.info(f"\n🏠 Property: {prop['title']}")
                logger.info(f"💰 Price: R{prop.get('price', 0):,}")
                logger.info(f"📍 Area: {prop['area']}")
                logger.info(f"🖼️  Images ({len(prop['images'])}):")
                for i, img in enumerate(prop['images'][:3]):
                    logger.info(f"   {i+1}. {img}")
                logger.info(f"🔗 URL: {prop.get('url')}")
                break
    else:
        logger.warning("No properties found")

def analyze_image_extraction_success():
    """
    Analyze how successful image extraction is across different areas
    """
    from scraper import Property24Scraper
    
    scraper = Property24Scraper()
    areas = ["sea-point", "camps-bay", "green-point"]
    
    stats = {}
    
    for area in areas:
        properties = scraper.scrape_area(area, max_pages=1, extract_images=True)
        
        total = len(properties)
        with_images = sum(1 for p in properties if p.get('images'))
        avg_images = sum(len(p.get('images', [])) for p in properties) / total if total > 0 else 0
        
        stats[area] = {
            "total": total,
            "with_images": with_images,
            "percentage": (with_images / total * 100) if total > 0 else 0,
            "avg_images_per_property": avg_images
        }
    
    logger.info("\n📊 Image Extraction Statistics:")
    for area, stat in stats.items():
        logger.info(f"\n{area}:")
        logger.info(f"  Total properties: {stat['total']}")
        logger.info(f"  With images: {stat['with_images']} ({stat['percentage']:.1f}%)")
        logger.info(f"  Avg images per property: {stat['avg_images_per_property']:.1f}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Test single property with images
            test_single_property_with_images()
        elif sys.argv[1] == "analyze":
            # Analyze image extraction success
            analyze_image_extraction_success()
        elif sys.argv[1] == "dry-run":
            # Run full scraper but don't send to backend
            run_scraper_and_import_with_images(dry_run=True, max_pages=1)
        else:
            # Run normal import
            run_scraper_and_import_with_images(max_pages=2)
    else:
        # Default: scrape and import with images
        logger.info("🚀 Running enhanced scraper with image extraction...")
        logger.info("   Use 'python property24_integration.py dry-run' to test without backend")
        logger.info("   Use 'python property24_integration.py test' to test single property")
        logger.info("   Use 'python property24_integration.py analyze' to analyze image extraction")
        
        run_scraper_and_import_with_images(
            areas=["sea-point", "green-point"],
            max_pages=1,
            extract_images=True
        )
        