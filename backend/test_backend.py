"""
Quick test script to verify backend is working properly
Run this after starting your backend server
"""

import requests
import json
from datetime import datetime

# API base URL
API_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running?")
        print("   Run: uvicorn main:app --reload")
        return False

def test_create_property():
    """Test creating a sample property"""
    print("\n🏠 Testing property creation...")
    
    sample_property = {
        "title": "Test Property - Sea Point Gem",
        "area": "Sea Point",
        "price": 1500000,
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqm": 85,
        "property_type": "Apartment",
        "url": "https://example.com/test-property",
        "images": ["https://via.placeholder.com/300"],
        "highlights": ["Ocean views", "Modern kitchen", "Secure parking"],
        "neighborhood_vibe": "Vibrant beachfront living with cafes"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/properties",
            json=sample_property,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Property created successfully!")
            print(f"   ID: {data['_id']}")
            print(f"   Title: {data['title']}")
            return data['_id']
        else:
            print(f"❌ Failed to create property: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating property: {e}")
        return None

def test_get_properties():
    """Test getting properties"""
    print("\n📋 Testing property retrieval...")
    
    try:
        response = requests.get(f"{API_URL}/api/properties")
        
        if response.status_code == 200:
            properties = response.json()
            print(f"✅ Retrieved {len(properties)} properties")
            
            if properties:
                print("   Sample property:")
                prop = properties[0]
                print(f"   - Title: {prop.get('title')}")
                print(f"   - Area: {prop.get('area')}")
                print(f"   - Price: R{prop.get('price', 0):,}")
            return True
        else:
            print(f"❌ Failed to get properties: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting properties: {e}")
        return False

def test_areas():
    """Test getting areas"""
    print("\n📍 Testing areas endpoint...")
    
    try:
        response = requests.get(f"{API_URL}/api/areas")
        
        if response.status_code == 200:
            areas = response.json()
            print(f"✅ Retrieved {len(areas)} areas")
            for area in areas[:3]:  # Show first 3
                print(f"   - {area['area']}: {area['property_count']} properties")
            return True
        else:
            print(f"❌ Failed to get areas: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting areas: {e}")
        return False

def test_scraper_import():
    """Test scraper import endpoint"""
    print("\n🔄 Testing scraper import...")
    
    sample_scraper_data = [
        {
            "title": "2 Bedroom Apartment",
            "area": "Camps Bay",
            "price": 2500000,
            "bedrooms": 2,
            "bathrooms": 2,
            "size_sqm": 95,
            "type": "Apartment",
            "url": "https://property24.com/test1",
            "selector_used": "div.listing"
        },
        {
            "title": "3 Bedroom House",
            "area": "Green Point",
            "price": 3200000,
            "bedrooms": 3,
            "bathrooms": 2,
            "size_sqm": 150,
            "type": "House",
            "url": "https://property24.com/test2",
            "selector_used": "div.property"
        }
    ]
    
    try:
        response = requests.post(
            f"{API_URL}/api/scraper/import",
            json=sample_scraper_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Scraper import successful!")
            print(f"   Processed: {result['processed']} properties")
            print(f"   Total in DB: {result['total_properties']}")
            return True
        else:
            print(f"❌ Failed to import: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error importing: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Cape Town Property Backend...")
    print("=" * 50)
    
    # Check if backend is running
    if not test_health():
        print("\n❗ Please start the backend first:")
        print("   cd backend")
        print("   uvicorn main:app --reload")
        return
    
    # Run tests
    test_create_property()
    test_get_properties()
    test_areas()
    test_scraper_import()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n📱 Your frontend should now be able to connect to:")
    print(f"   {API_URL}")
    print("\n📚 View API documentation at:")
    print(f"   {API_URL}/docs")

if __name__ == "__main__":
    main()
    