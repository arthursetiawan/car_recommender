import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import json
import re

# More realistic headers to avoid detection
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Referer': 'https://www.cargurus.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def scrape_cargurus(base_url):
    all_cars = []
    page = 1
    max_pages = 5  # Limit to prevent excessive scraping during testing
    
    while page <= max_pages:
        # Construct URL with page parameter
        if page == 1:
            url = base_url
        else:
            # Add page parameter to URL
            if "?" in base_url:
                url = f"{base_url}&page={page}"
            else:
                url = f"{base_url}?page={page}"
        
        print(f"Scraping page {page}...")
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"Failed to retrieve page {page}: Status code {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Method 1: Try to find the car listings in the HTML directly
            # Look for car listing containers
            listing_containers = soup.select("div.ft-listing-wide-inner")
            
            if not listing_containers:
                # Try alternative selectors
                listing_containers = soup.select("div[data-cg-ft='srp-listing-card']")
            
            if not listing_containers:
                listing_containers = soup.select("div.ListingRowContainerstyles__Container-sc-puks2y-0")
            
            # If we found listings via HTML, process them
            if listing_containers:
                print(f"Found {len(listing_containers)} listings via HTML")
                for container in listing_containers:
                    try:
                        car = {}
                        
                        # Extract title
                        title_elem = container.select_one("h4.cardContent__title")
                        if not title_elem:
                            title_elem = container.select_one("h2.cg-listingDetail-model")
                        if not title_elem:
                            title_elem = container.select_one("h2")  # Fallback to any h2
                            
                        if title_elem:
                            car["title"] = title_elem.text.strip()
                        
                        # Extract price
                        price_elem = container.select_one("span.cg-dealFinder-price")
                        if not price_elem:
                            price_elem = container.select_one("span.cardContent__price")
                        if not price_elem:
                            price_elem = container.select_one("span[data-cg-ft='srp-listing-price']")
                        if not price_elem:
                            # Try any element with $ in it
                            price_text = container.find(string=re.compile(r'\$[\d,]+'))
                            if price_text:
                                car["price"] = price_text.strip()
                        else:
                            car["price"] = price_elem.text.strip()
                        
                        # Extract mileage
                        mileage_elem = container.select_one("div.cg-dealFinder-mileage")
                        if not mileage_elem:
                            mileage_elem = container.select_one("p[data-cg-ft='srp-listing-mileage']")
                        if not mileage_elem:
                            # Try to find by text pattern (e.g., "123,456 mi")
                            mileage_text = container.find(string=re.compile(r'[\d,]+ mi'))
                            if mileage_text:
                                car["mileage"] = mileage_text.strip()
                        else:
                            car["mileage"] = mileage_elem.text.strip()
                        
                        # Extract location
                        location_elem = container.select_one("div.cg-dealFinder-location")
                        if not location_elem:
                            location_elem = container.select_one("p.cardContent__location")
                        
                        if location_elem:
                            car["location"] = location_elem.text.strip()
                        
                        # Features/details
                        features = []
                        feature_elems = container.select("ul.cg-dealFinder-features li")
                        if feature_elems:
                            for elem in feature_elems:
                                features.append(elem.text.strip())
                            car["features"] = ", ".join(features)
                        
                        if car:  # Only add if we found some data
                            all_cars.append(car)
                    except Exception as e:
                        print(f"Error parsing listing: {e}")
            else:
                # Method 2: Try to extract from JavaScript data
                print("No listings found via HTML, trying JavaScript extraction...")
                scripts = soup.find_all("script", {"type": "text/javascript"})
                
                data_extracted = False
                for script in scripts:
                    if not script.string:
                        continue
                        
                    script_text = script.string
                    
                    # Look for listing data in various formats
                    data_patterns = [
                        r'window\.__INITIAL_STATE__\s*=\s*({.*});',
                        r'window\.cg\.initialData\s*=\s*({.*});',
                        r'window\.carData\s*=\s*({.*});',
                        r'var\s+listings\s*=\s*(\[.*\]);'
                    ]
                    
                    for pattern in data_patterns:
                        match = re.search(pattern, script_text, re.DOTALL)
                        if match:
                            try:
                                json_text = match.group(1)
                                data = json.loads(json_text)
                                
                                # Navigate to listings (structure varies)
                                if isinstance(data, list):
                                    # Direct list of listings
                                    listings = data
                                elif "listings" in data:
                                    listings = data["listings"]
                                elif "searchResults" in data and "listings" in data["searchResults"]:
                                    listings = data["searchResults"]["listings"]
                                else:
                                    # Try to find array with car objects
                                    listings = find_listings_in_json(data)
                                
                                if listings and isinstance(listings, list):
                                    print(f"Found {len(listings)} listings via JavaScript")
                                    cars = parse_json_listings(listings)
                                    all_cars.extend(cars)
                                    data_extracted = True
                                    break
                            except Exception as e:
                                print(f"Error parsing script JSON: {e}")
                    
                    if data_extracted:
                        break
                        
                if not data_extracted:
                    print("Could not extract listing data from JavaScript")
            
            # Check for more pages
            next_page_exists = False
            
            # Try different selectors for pagination
            next_button = soup.select_one("a[data-cg-ft='page-nav-next-page']")
            if not next_button:
                next_button = soup.select_one("a.nextPageElement")
            if not next_button:
                next_button = soup.select_one("a.pagination__button--next")
                
            if next_button and "disabled" not in next_button.get("class", []):
                next_page_exists = True
            
            if not next_page_exists:
                print("No more pages available")
                break
            
            # Random delay between requests
            delay = random.uniform(3, 7)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
            
            page += 1
            
        except Exception as e:
            print(f"Error scraping page {page}: {e}")
            break
    
    return all_cars

def find_listings_in_json(data):
    """Recursively search for an array that looks like car listings"""
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        # Check if this looks like car listings
        car_related_keys = ['price', 'mileage', 'year', 'make', 'model', 'vin']
        sample_item = data[0]
        matching_keys = sum(1 for key in car_related_keys if key in sample_item)
        if matching_keys >= 2:  # If it has at least 2 car-related keys
            return data
    
    if isinstance(data, dict):
        for key, value in data.items():
            result = find_listings_in_json(value)
            if result:
                return result
    
    return None

def parse_json_listings(listings_data):
    """Parse car listings from JSON data"""
    cars = []
    
    for listing in listings_data:
        try:
            car = {}
            
            # Check for common property names in various formats
            # Title/Name
            for key in ['title', 'listingTitle', 'name', 'vehicleTitle', 'heading']:
                if key in listing:
                    car["title"] = listing[key]
                    break
            
            # If no direct title, try to construct from year, make, model
            if "title" not in car:
                title_parts = []
                for key in ['year', 'make', 'model', 'trim']:
                    if key in listing and listing[key]:
                        title_parts.append(str(listing[key]))
                if title_parts:
                    car["title"] = " ".join(title_parts)
            
            # Price
            for key in ['price', 'listingPrice', 'displayPrice', 'priceString']:
                if key in listing:
                    value = listing[key]
                    if isinstance(value, (int, float)):
                        car["price"] = f"${value:,}"
                    else:
                        car["price"] = value
                    break
            
            # Mileage
            for key in ['mileage', 'odometer', 'mileageString']:
                if key in listing:
                    value = listing[key]
                    if isinstance(value, (int, float)):
                        car["mileage"] = f"{value:,} mi"
                    else:
                        car["mileage"] = value
                    break
            
            # Location
            if "dealer" in listing and isinstance(listing["dealer"], dict):
                dealer = listing["dealer"]
                location_parts = []
                for key in ['city', 'state']:
                    if key in dealer and dealer[key]:
                        location_parts.append(dealer[key])
                if location_parts:
                    car["location"] = ", ".join(location_parts)
            
            # Try direct location properties
            if "location" not in car:
                for key in ['location', 'sellerLocation', 'dealerLocation']:
                    if key in listing:
                        car["location"] = listing[key]
                        break
            
            # Additional details
            details = {}
            # Try to extract any additional useful info
            for key in ['bodyStyle', 'transmission', 'driveTrain', 'exteriorColor', 'interiorColor',
                       'engine', 'fuelType', 'mpg', 'sellerRating', 'dealScore', 'vin']:
                if key in listing:
                    details[key] = listing[key]
            
            if details:
                car["details"] = details
            
            if car and "title" in car:  # Only add if we have at least a title
                cars.append(car)
                
        except Exception as e:
            print(f"Error parsing JSON listing: {e}")
    
    return cars

if __name__ == "__main__":
    # Use the specific URL you provided
    url = "https://www.cargurus.com/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action?sourceContext=carGurusHomePageModel&entitySelectingHelper.selectedEntity=&zip=98037"
    
    car_data = scrape_cargurus(url)
    
    if car_data:
        print(f"\nSuccessfully scraped {len(car_data)} car listings")
        
        # Save to CSV
        df = pd.DataFrame(car_data)
        df.to_csv('cargurus_car_data.csv', index=False, encoding='utf-8')
        print(f"Data saved to cargurus_car_data.csv")
        
        # Print first few entries as a sample
        print("\nSample data:")
        for car in car_data[:3]:
            print(car)
    else:
        print("No car data was collected.")