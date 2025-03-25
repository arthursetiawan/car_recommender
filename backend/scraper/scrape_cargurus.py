import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from fake_useragent import UserAgent
import logging

# Set up logging - test cert changes - f4f4f4
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Random header function to mimic realistic user agent
def get_random_headers():
    # Create a UserAgent object for random realistic user agents
    try:
        ua = UserAgent()
        user_agent = ua.random
    except:
        # Fallback list of user agents if fake_useragent fails
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        user_agent = random.choice(user_agents)
    
    # More extensive and realistic headers X
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    return headers

# Human like delay!
def human_like_delay():
    """Simulate more realistic human browsing behavior with variable delays"""
    # Base delay between 3-7 seconds
    base_delay = random.uniform(3, 7)
    
    # Occasionally (20% chance) add a longer pause (10-15 seconds)
    if random.random() < 0.2:
        base_delay += random.uniform(10, 15)
        
    return base_delay

def scrape_cargurus(base_url, max_pages=5):
    all_cars = []
    page = 1
    
    # Use a session to maintain cookies and other state
    session = requests.Session()
    
    # Initial visit to homepage to get cookies
    try:
        logger.info("Visiting homepage to set initial cookies...")
        home_resp = session.get("https://www.cargurus.com/", headers=get_random_headers())
        if home_resp.status_code != 200:
            logger.warning(f"Failed to access homepage: {home_resp.status_code}")
    except Exception as e:
        logger.error(f"Error accessing homepage: {e}")
    
    # Add a delay after homepage visit
    time.sleep(human_like_delay())
    
    while page <= max_pages:
        # Construct URL with page parameter
        if page == 1:
            url = base_url
        else:
            if "?" in base_url:
                url = f"{base_url}&page={page}"
            else:
                url = f"{base_url}?page={page}"
        
        logger.info(f"Scraping page {page}...")
        
        try:
            # Get new headers for each request
            headers = get_random_headers()
            
            # Add a refer that looks like we're coming from previous pages
            if page > 1:
                prev_page_url = f"{base_url}{'&' if '?' in base_url else '?'}page={page-1}"
                headers['Referer'] = prev_page_url
            
            # Make the request with the session
            response = session.get(url, headers=headers, timeout=30)
            
            # Check response
            if response.status_code == 403:
                logger.error(f"Access forbidden (403) on page {page}. Detected as a bot.")
                logger.info("Trying with different approach...")
                
                # Wait longer and try again with different headers
                time.sleep(random.uniform(20, 30))
                headers = get_random_headers()
                headers['Referer'] = 'https://www.cargurus.com/'
                response = session.get(url, headers=headers, timeout=30)
                
                if response.status_code == 403:
                    logger.error("Still getting 403 error after retry.")
                    break
            
            if response.status_code != 200:
                logger.error(f"Failed to retrieve page {page}: Status code {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Check if we got a CAPTCHA or login page
            if "captcha" in response.text.lower() or "robot" in response.text.lower():
                logger.error("CAPTCHA or robot detection page encountered")
                break
                
            # Find all card elements using more flexible selectors
            listing_containers = soup.select("div[data-testid='srp-tile-body']")
            
            if not listing_containers:
                logger.warning(f"No listings found on page {page}. Trying alternative selectors...")
                
                # Try alternative selectors
                listing_containers = soup.select("div.cKGqZX, div.LIyLk")
                
                if not listing_containers:
                    logger.warning("Still no listings found. This could mean the page structure has changed.")
                    
                    # Save the HTML for debugging
                    with open(f"debug_page_{page}.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    logger.info(f"Saved HTML to debug_page_{page}.html for inspection")
                    break
            
            logger.info(f"Found {len(listing_containers)} listings")
            
            for container in listing_containers:
                try:
                    car = {}
                    
                    # Title - trying multiple possible selectors
                    title_elem = (container.select_one("h4.WoAzt.dzuXc") or 
                                 container.select_one("h4[data-testid='listing-title']") or
                                 container.select_one("h4.listing-title"))
                    if title_elem:
                        car["title"] = title_elem.text.strip()
                    
                    # Price - trying multiple possible selectors
                    price_elem = (container.select_one("h4[data-testid='srp-tile-price']") or
                                 container.select_one("span.price") or
                                 container.select_one("h4.price"))
                    if price_elem:
                        car["price"] = price_elem.text.strip()
                    
                    # Mileage
                    mileage_elem = (container.select_one("p[data-testid='srp-tile-mileage']") or
                                   container.select_one("p.mileage"))
                    if mileage_elem:
                        car["mileage"] = mileage_elem.text.strip()
                    
                    # Engine
                    engine_elem = (container.select_one("p[data-testid='seo-srp-tile-engine-display-name']") or
                                  container.select_one("p.engine"))
                    if engine_elem:
                        car["engine"] = engine_elem.text.strip()
                    
                    # More generic approach to extract text from various elements
                    for elem in container.select("p, span, div"):
                        text = elem.text.strip()
                        if text and "mi" in text and "mileage" not in car:
                            car["mileage"] = text
                        elif text and ("L" in text or "cylinder" in text.lower()) and "engine" not in car:
                            car["engine"] = text
                    
                    if car:  # Only add if we found some data
                        all_cars.append(car)
                except Exception as e:
                    logger.error(f"Error parsing listing: {e}")
            
            # Check for next page - look for the next page button
            next_button = soup.select_one("a[data-cg-ft='page-nav-next-page']")
            if not next_button or "disabled" in next_button.get("class", []):
                logger.info("No more pages available")
                break
            
            # Human-like delay between requests
            delay = human_like_delay()
            logger.info(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
            
            page += 1
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on page {page}: {e}")
            break
        except Exception as e:
            logger.error(f"Error scraping page {page}: {e}")
            break
    
    return all_cars

if __name__ == "__main__":
    # Use the specific URL you provided
    url = "https://www.cargurus.com/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action?sourceContext=carGurusHomePageModel&entitySelectingHelper.selectedEntity=&zip=98037"
    
    logger.info("Starting the scraper...")
    car_data = scrape_cargurus(url, max_pages=3)
    
    if car_data:
        logger.info(f"Successfully scraped {len(car_data)} car listings")
        
        # Save to CSV
        df = pd.DataFrame(car_data)
        df.to_csv('cargurus_car_data.csv', index=False, encoding='utf-8')
        logger.info(f"Data saved to cargurus_car_data.csv")
        
        # Print first few entries as a sample
        logger.info("Sample data:")
        for i, car in enumerate(car_data[:3], 1):
            print(f"Car {i}:")
            for k, v in car.items():
                print(f"  {k}: {v}")
            print()
    else:
        logger.error("No car data was collected.")