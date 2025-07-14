"""
Check and fix the backend to ensure images are saved
"""

import requests
import json

def check_property_model():
    """Check if the backend Property model includes images"""
    
    print("🔍 Checking backend Property model...\n")
    
    # First, let's see what fields are returned by the API
    response = requests.get("http://localhost:8000/api/properties?limit=1")
    if response.status_code == 200 and response.json():
        property_example = response.json()[0]
        print("Fields in API response:")
        for field in property_example.keys():
            print(f"  - {field}")
        
        if 'images' in property_example:
            print("\n✅ 'images' field exists in API response")
        else:
            print("\n❌ 'images' field MISSING from API response!")
    
    # Check the OpenAPI schema
    print("\n📋 Checking API documentation...")
    try:
        response = requests.get("http://localhost:8000/openapi.json")
        if response.status_code == 200:
            openapi = response.json()
            # Look for PropertyResponse schema
            schemas = openapi.get('components', {}).get('schemas', {})
            prop_response = schemas.get('PropertyResponse', {})
            if prop_response:
                properties = prop_response.get('properties', {})
                if 'images' in properties:
                    print("✅ 'images' field defined in PropertyResponse schema")
                    print(f"   Type: {properties['images']}")
                else:
                    print("❌ 'images' field NOT in PropertyResponse schema!")
    except:
        pass

def test_direct_property_creation():
    """Test creating a property directly (not via scraper import)"""
    
    print("\n\n🧪 Testing direct property creation with images...")
    
    test_property = {
        "title": "Direct Test Property",
        "area": "test-area",
        "price": 999999,
        "bedrooms": 2,
        "bathrooms": 1,
        "size_sqm": 80,
        "property_type": "Apartment",
        "images": [
            "https://test.com/image1.jpg",
            "https://test.com/image2.jpg",
            "https://test.com/image3.jpg"
        ],
        "highlights": ["Test Feature 1", "Test Feature 2"]
    }
    
    # Create via direct API
    response = requests.post(
        "http://localhost:8000/api/properties",
        json=test_property,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        created = response.json()
        print(f"✅ Created property: {created.get('title')}")
        print(f"   ID: {created.get('id', created.get('_id'))}")
        print(f"   Images in response: {len(created.get('images', []))}")
        
        if created.get('images'):
            print("   ✅ Direct creation PRESERVES images!")
        else:
            print("   ❌ Direct creation LOSES images!")
            
        return created.get('id', created.get('_id'))
    else:
        print(f"❌ Creation failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def check_convert_function():
    """The issue might be in convert_scraper_output_to_property function"""
    
    print("\n\n🔍 Issue likely in backend's convert_scraper_output_to_property()...")
    print("\nThe function in models/property.py might not be handling images.")
    print("\nCheck if it includes this line:")
    print("    images=scraper_data.get('images', []),")
    print("\nOr it might be using the wrong key.")

def manual_fix_suggestion():
    """Suggest the manual fix needed"""
    
    print("\n\n🔧 MANUAL FIX NEEDED:")
    print("\nIn your backend's models/property.py, find the convert_scraper_output_to_property function")
    print("and make sure it includes:")
    print("""
def convert_scraper_output_to_property(scraper_data: dict) -> PropertyCreate:
    property_data = PropertyCreate(
        title=scraper_data.get("title", "Property"),
        area=scraper_data.get("area", "Unknown"),
        price=scraper_data.get("price"),
        bedrooms=scraper_data.get("bedrooms"),
        bathrooms=scraper_data.get("bathrooms"),
        size_sqm=scraper_data.get("size_sqm"),
        property_type=scraper_data.get("type", "Property"),
        url=scraper_data.get("url"),
        images=scraper_data.get("images", []),  # ← THIS LINE IS CRITICAL!
        highlights=scraper_data.get("highlights", []),
        neighborhood_vibe=scraper_data.get("neighborhood_vibe"),
        selector_used=scraper_data.get("selector_used"),
        listed_date=datetime.now()
    )
    return property_data
""")

if __name__ == "__main__":
    check_property_model()
    property_id = test_direct_property_creation()
    check_convert_function()
    manual_fix_suggestion()