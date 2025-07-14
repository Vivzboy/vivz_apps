"""
Property24 Web Scraper - Enhanced Version with Image Extraction
Combines the working pagination scraper with image extraction capabilities
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
import json
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Property24 Area Codes
PROPERTY24_AREA_CODES = {
    "sea-point": 11021,
    "green-point": 11017,
    "camps-bay": 11014,
    "clifton": 11015,
    "fresnaye": 11016,
    "mouille-point": 11018,
    "de-waterkant": 9141,
    "gardens": 9145,
    "oranjezicht": 9155,
    "tamboerskloof": 9163,
    "vredehoek": 9166,
}


class Property24Scraper:
    """
    Enhanced Property24 scraper with image extraction capabilities
    """
    
    def __init__(self, delay_between_requests: float = 1.0):
        self.delay = delay_between_requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
    
    def extract_property_images(self, element) -> List[str]:
        """
        Extract image URLs from property listing element
        """
        images = []
        
        try:
            # Method 1: Look for img tags with data-src or src
            img_tags = element.find_all('img')
            for img in img_tags:
                # Skip icons and small images
                if 'icon' in str(img.get('class', [])):
                    continue
                
                # Try data-src first (lazy loading), then src
                img_url = img.get('data-src') or img.get('src')
                
                if img_url:
                    # Skip base64 images and placeholders
                    if 'data:image' in img_url or 'placeholder' in img_url:
                        continue
                    
                    # Ensure full URL
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url if img_url.startswith('//') else 'https://www.property24.com' + img_url
                    
                    # Check if it's a property image (usually contains certain patterns)
                    if any(pattern in img_url for pattern in ['property24', 'listing', 'property', 'p24']):
                        images.append(img_url)
            
            # Method 2: Look for background images in style attributes
            elements_with_bg = element.find_all(style=re.compile('background-image'))
            for el in elements_with_bg:
                style = el.get('style', '')
                bg_match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                if bg_match:
                    img_url = bg_match.group(1)
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url if img_url.startswith('//') else 'https://www.property24.com' + img_url
                    if 'property' in img_url or 'listing' in img_url:
                        images.append(img_url)
            
            # Method 3: Look for gallery data in JSON
            scripts = element.find_all('script', type='application/json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    # Property24 often stores images in JSON
                    if isinstance(data, dict):
                        self._extract_images_from_json(data, images)
                except:
                    pass
            
            # Remove duplicates while preserving order
            seen = set()
            unique_images = []
            for img in images:
                if img not in seen:
                    seen.add(img)
                    unique_images.append(img)
            
            return unique_images[:5]  # Limit to 5 images per property
            
        except Exception as e:
            logger.debug(f"Error extracting images: {e}")
            return []
    
    def _extract_images_from_json(self, data: dict, images: list, depth: int = 0):
        """Recursively extract image URLs from JSON data"""
        if depth > 5:  # Prevent too deep recursion
            return
        
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['images', 'gallery', 'photos', 'imageUrl', 'image']:
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item.startswith('http'):
                                images.append(item)
                            elif isinstance(item, dict) and 'url' in item:
                                images.append(item['url'])
                elif isinstance(value, (dict, list)):
                    self._extract_images_from_json(value, images, depth + 1)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._extract_images_from_json(item, images, depth + 1)
        
    def scrape_area(self, area: str, transaction_type: str = "for-sale", 
                    max_pages: int = None, extract_images: bool = True) -> List[Dict]:
        """
        Scrape all properties from a specific area with pagination
        
        Args:
            area: Area to scrape
            transaction_type: "for-sale" or "to-rent"
            max_pages: Maximum number of pages to scrape
            extract_images: Whether to extract images (adds slight overhead)
        """
        area_normalized = area.lower().replace(" ", "-").replace("_", "-")
        area_code = PROPERTY24_AREA_CODES.get(area_normalized)
        
        if not area_code:
            logger.error(f"Unknown area: {area}")
            return []
        
        all_properties = []
        seen_urls = set()
        page = 1
        consecutive_empty_pages = 0
        
        logger.info(f"Scraping {area} ({transaction_type})")
        
        while True:
            if consecutive_empty_pages >= 2:
                break
                
            if max_pages and page > max_pages:
                break
            
            # Build URL - EXACTLY as in working version
            url = f"https://www.property24.com/{transaction_type}/{area_normalized}/cape-town/western-cape/{area_code}"
            if page > 1:
                url += f"?Page={page}"
            
            logger.info(f"Page {page}: {url}")
            
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code != 200:
                    logger.error(f"Bad status code: {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract using the enhanced method
                page_properties = self._extract_all_properties_from_page(soup, area, extract_images)
                
                # Filter duplicates
                new_properties = []
                for prop in page_properties:
                    prop_url = prop.get('url', '')
                    if prop_url and prop_url not in seen_urls:
                        seen_urls.add(prop_url)
                        new_properties.append(prop)
                    elif not prop_url:
                        # Include properties without URLs too
                        new_properties.append(prop)
                
                if new_properties:
                    all_properties.extend(new_properties)
                    logger.info(f"✅ Found {len(new_properties)} new properties")
                    consecutive_empty_pages = 0
                else:
                    logger.warning(f"No new properties on page {page}")
                    consecutive_empty_pages += 1
                
                page += 1
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"Error on page {page}: {str(e)}")
                break
        
        logger.info(f"✅ Total properties found: {len(all_properties)}")
        return all_properties
    
    def _extract_all_properties_from_page(self, soup: BeautifulSoup, area: str, extract_images: bool = True) -> List[Dict]:
        """
        Extract properties using EXACT method from working pagination scraper
        """
        all_properties = []
        seen_prices_and_beds = set()
        
        # EXACT selectors from working version
        selectors = [
            'div[class*="listing"]',
            'div[class*="p24_"]',
            'div[class*="tile"]',
            'div[class*="property"]',
            'article[class*="listing"]',
            'div[class*="result"]',
            '.p24_regularTile',
            '.js_listingTile',
            '[data-listing-number]',
            'div[class*="sc_listingTile"]',
            'div[class*="ListingTile"]',
            'div[class*="propertyTile"]',
            'a[href*="/for-sale/"][href*="plId="]',
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            
            if elements:
                for element in elements:
                    # Handle link elements - get parent container
                    if element.name == 'a':
                        container = element.parent
                        while container and len(container.get_text()) < 50:
                            container = container.parent
                    else:
                        container = element
                    
                    if container:
                        prop = self._extract_property_data_enhanced(container, extract_images)
                        
                        if prop:
                            # Unique key to avoid duplicates
                            key = (prop.get('price'), prop.get('bedrooms'), prop.get('size_sqm'))
                            if key not in seen_prices_and_beds:
                                seen_prices_and_beds.add(key)
                                prop['area'] = area
                                prop['selector_used'] = selector
                                all_properties.append(prop)
        
        return all_properties
    
    def _extract_property_data_enhanced(self, element, extract_images: bool = True) -> Optional[Dict]:
        """
        Enhanced extraction that includes images and more details
        """
        text = element.get_text(separator=' ', strip=True)
        
        # Skip if too short or too long
        if len(text) < 30 or len(text) > 2000:
            return None
        
        property_data = {}
        
        # Extract price - EXACT patterns that worked
        price_match = re.search(r'R\s*(\d{1,3}(?:[\s,]*\d{3})+)', text)
        if price_match:
            try:
                price_str = price_match.group(1).replace(',', '').replace(' ', '')
                property_data['price'] = int(price_str)
            except:
                pass
        elif 'development' in text.lower():
            property_data['price'] = None
            property_data['type'] = 'Development'
        else:
            return None  # No price, skip
        
        # Extract bedrooms
        bed_match = re.search(r'(\d+)\s*[Bb]ed', text)
        if bed_match:
            property_data['bedrooms'] = int(bed_match.group(1))
        
        # Extract bathrooms
        bath_match = re.search(r'(\d+)\s*[Bb]ath', text)
        if bath_match:
            property_data['bathrooms'] = int(bath_match.group(1))
        
        # Extract size
        size_match = re.search(r'(\d+)\s*m[²2]', text, re.IGNORECASE)
        if size_match:
            property_data['size_sqm'] = int(size_match.group(1))
        
        # Property type
        text_lower = text.lower()
        if 'apartment' in text_lower or 'flat' in text_lower:
            property_data['type'] = 'Apartment'
        elif 'house' in text_lower:
            property_data['type'] = 'House'
        elif 'townhouse' in text_lower:
            property_data['type'] = 'Townhouse'
        else:
            property_data['type'] = property_data.get('type', 'Property')
        
        # Extract URL
        link = element.find('a', href=True)
        if link and '/for-sale/' in link['href']:
            href = link['href']
            property_data['url'] = href if href.startswith('http') else 'https://www.property24.com' + href
        
        # Extract images if requested
        if extract_images:
            images = self.extract_property_images(element)
            if images:
                property_data['images'] = images
                logger.debug(f"Found {len(images)} images for property")
        
        # Extract additional features from text
        features = []
        feature_patterns = [
            (r'pool', 'Pool'),
            (r'garage|parking', 'Parking'),
            (r'garden', 'Garden'),
            (r'security', 'Security'),
            (r'balcony', 'Balcony'),
            (r'pet[\s-]?friendly', 'Pet Friendly'),
            (r'furnished', 'Furnished'),
            (r'sea[\s-]?view|ocean[\s-]?view', 'Sea Views'),
            (r'mountain[\s-]?view', 'Mountain Views')
        ]
        
        for pattern, feature in feature_patterns:
            if re.search(pattern, text_lower):
                features.append(feature)
        
        if features:
            property_data['highlights'] = features
        
        # Create title
        if property_data.get('bedrooms'):
            property_data['title'] = f"{property_data['bedrooms']} Bedroom {property_data['type']}"
        else:
            property_data['title'] = property_data['type']
        
        # Add area description if found
        if 'walking distance' in text_lower:
            property_data['neighborhood_vibe'] = "Walking distance to amenities"
        
        return property_data
    
    def _extract_property_data_simple(self, element) -> Optional[Dict]:
        """
        Simple extraction without images (for backwards compatibility)
        """
        return self._extract_property_data_enhanced(element, extract_images=False)
    
    def scrape_property_details_page(self, url: str) -> Dict:
        """
        Scrape detailed information from individual property page
        This gets much more data including all images
        """
        try:
            logger.info(f"Fetching details from: {url}")
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch property page: {response.status_code}")
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            details = {}
            
            # Extract all images from gallery
            gallery_images = []
            
            # Method 1: Look for image gallery container
            gallery_container = soup.find('div', class_=re.compile('gallery|carousel|slider|images'))
            if gallery_container:
                images = self.extract_property_images(gallery_container)
                gallery_images.extend(images)
            
            # Method 2: Look for all property images on page
            all_images = soup.find_all('img', src=re.compile('property|listing|p24'))
            for img in all_images:
                src = img.get('src') or img.get('data-src')
                if src and src not in gallery_images:
                    if not src.startswith('http'):
                        src = 'https:' + src if src.startswith('//') else 'https://www.property24.com' + src
                    gallery_images.append(src)
            
            details['images'] = gallery_images[:10]  # Limit to 10 images
            
            # Extract description
            description_el = soup.find('div', class_=re.compile('description|content|details'))
            if description_el:
                details['description'] = description_el.get_text(strip=True)[:500]
            
            return details
            
        except Exception as e:
            logger.error(f"Error scraping property details: {e}")
            return {}
    
    def scrape_multiple_areas(self, areas: List[str], transaction_type: str = "for-sale",
                            max_pages_per_area: int = None, extract_images: bool = True) -> pd.DataFrame:
        """
        Scrape multiple areas with optional image extraction
        """
        all_properties = []
        
        for i, area in enumerate(areas):
            logger.info(f"\nArea {i+1}/{len(areas)}: {area}")
            logger.info("=" * 60)
            
            properties = self.scrape_area(area, transaction_type, max_pages=max_pages_per_area, extract_images=extract_images)
            all_properties.extend(properties)
            
            if i < len(areas) - 1:
                time.sleep(self.delay * 2)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_properties)
        
        if not df.empty and 'price' in df.columns and 'size_sqm' in df.columns:
            df['price_per_sqm'] = df.apply(
                lambda row: row['price'] / row['size_sqm'] 
                if pd.notna(row.get('price')) and pd.notna(row.get('size_sqm')) and row['size_sqm'] > 0 
                else None,
                axis=1
            )
        
        return df
    
    def save_results(self, df: pd.DataFrame, filename: str = None):
        """
        Save results to CSV
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"property24_results_{timestamp}.csv"
        
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(df)} properties to {filename}")


# Example usage
if __name__ == "__main__":
    scraper = Property24Scraper()
    
    # Scrape with image extraction enabled
    properties = scraper.scrape_area("sea-point", max_pages=1, extract_images=True)
    
    print(f"Total properties found: {len(properties)}")
    
    # Show some sample results
    for prop in properties[:3]:
        price = prop.get('price')
        price_str = f"R{price:,}" if price else "Price on Application"
        
        print(f"\n{prop.get('title', 'Unknown')} - {price_str}")
        print(f"Area: {prop.get('area')}")
        print(f"Images found: {len(prop.get('images', []))}")
        if prop.get('images'):
            print(f"First image: {prop['images'][0]}")
        if prop.get('highlights'):
            print(f"Features: {', '.join(prop['highlights'])}")