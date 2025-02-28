import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# Headers to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Referer': 'https://www.cargurus.com/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}

def scrape_cargurus(base_url, max_pages=5):
    all_cars = []
    page = 1
    
    while page <= max_pages:
        # Construct URL with page parameter
        if page == 1:
            url = base_url
        else:
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
            
            # Find all card elements using the exact class from your example
            listing_containers = soup.select("div[data-testid='srp-tile-body']")
            
            if not listing_containers:
                print(f"No listings found on page {page}")
                break
                
            print(f"Found {len(listing_containers)} listings")
            
            for container in listing_containers:
                try:
                    car = {}
                    
                    # Title - using the exact selector from your example
                    title_elem = container.select_one("h4.WoAzt.dzuXc")
                    if title_elem:
                        car["title"] = title_elem.text.strip()
                    
                    # Price
                    price_elem = container.select_one("h4[data-testid='srp-tile-price']")
                    if price_elem:
                        car["price"] = price_elem.text.strip()
                    
                    # Mileage
                    mileage_elem = container.select_one("p[data-testid='srp-tile-mileage']")
                    if mileage_elem:
                        car["mileage"] = mileage_elem.text.strip()
                    
                    # Engine
                    engine_elem = container.select_one("p[data-testid='seo-srp-tile-engine-display-name']")
                    if engine_elem:
                        car["engine"] = engine_elem.text.strip()
                    
                    # Features
                    features_elem = container.select_one("div[data-testid='srp-tile-horizontal-truncated-list']")
                    if features_elem:
                        car["features"] = features_elem.text.strip()
                    
                    # Deal rating
                    deal_rating_elem = container.select_one("div[data-testid='srp-tile-deal-rating'] span.x-nqd")
                    if deal_rating_elem:
                        car["deal_rating"] = deal_rating_elem.text.strip()
                    
                    # Monthly payment estimate
                    monthly_payment_elem = container.select_one("div._monthlyPayment_2ixny_7 span")
                    if monthly_payment_elem:
                        car["monthly_payment"] = monthly_payment_elem.text.strip()
                    
                    # Phone number
                    phone_elem = container.select_one("button[data-testid='button-phone-number']")
                    if phone_elem:
                        car["phone"] = phone_elem.text.strip()
                    
                    # Dealer/Sponsor information
                    sponsor_elem = container.select_one("div[data-testid='srp-tile-eyebrow']")
                    if sponsor_elem:
                        car["dealer_info"] = sponsor_elem.text.strip()
                    
                    if car:  # Only add if we found some data
                        all_cars.append(car)
                except Exception as e:
                    print(f"Error parsing listing: {e}")
            
            # Check for next page - look for the next page button
            next_button = soup.select_one("a[data-cg-ft='page-nav-next-page']")
            if not next_button or "disabled" in next_button.get("class", []):
                print("No more pages available")
                break
            
            # Random delay between requests
            delay = random.uniform(2, 5)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
            
            page += 1
            
        except Exception as e:
            print(f"Error scraping page {page}: {e}")
            break
    
    return all_cars

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
        for i, car in enumerate(car_data[:3], 1):
            print(f"Car {i}:")
            for k, v in car.items():
                print(f"  {k}: {v}")
            print()
    else:
        print("No car data was collected.")