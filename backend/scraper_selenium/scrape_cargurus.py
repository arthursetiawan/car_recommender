import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Set up Selenium WebDriver
def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    logger.info("Setting up the WebDriver.")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Scrape CarGurus listings
def scrape_cargurus(url, max_pages=3):
    driver = setup_driver()
    driver.get(url)
    time.sleep(5)  # Wait for page to load
    
    logger.info("Waiting for page to load...")
    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='srp-listing-tile']")))

    all_cars = []
    
    for page in range(1, max_pages + 1):
        logger.info(f"Scraping page {page}...")
        
        # Wait for listings to be present
        try:
            listings = driver.find_elements(By.CSS_SELECTOR, """div[data-testid="srp-listing-tile"]""")
            logger.info(f"Found {len(listings)} listings on page {page}")
        except Exception as e:
            logger.error(f"Error finding listings on page {page}: {e}")
            break
        
        for listing in listings:
            try:
                car = {}
                
                # Get car title
                car["title"] = listing.find_element(By.CSS_SELECTOR, "h4[data-testid='srp-tile-listing-title']").text
                logger.debug(f"Found title: {car['title']}")
                
                # Get car price
                car["price"] = listing.find_element(By.CSS_SELECTOR, "h4[data-testid='srp-tile-price']").text
                logger.debug(f"Found price: {car['price']}")
                
                # Get car mileage
                car["mileage"] = listing.find_element(By.CSS_SELECTOR, "p[data-testid='srp-tile-mileage']").text
                logger.debug(f"Found mileage: {car['mileage']}")
                
                # Get car location (dealer info)
                car["location"] = listing.find_element(By.CSS_SELECTOR, "p[data-testid='srp-tile-bucket-text']").text
                logger.debug(f"Found location: {car['location']}")
                
                # Get car image (optional)
                car["image_url"] = listing.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
                logger.debug(f"Found image URL: {car['image_url']}")
                
                all_cars.append(car)
            except Exception as e:
                logger.error(f"Error extracting car details: {e}")
                continue

        # Try to click next page button (if present)
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Next']")
            next_button.click()
            logger.info(f"Clicking next page button.")
            time.sleep(3)  # Wait for the next page to load
        except Exception as e:
            logger.info("No more pages or next button not found.")
            break
    
    driver.quit()
    logger.info("Scraping completed.")
    return all_cars

if __name__ == "__main__":
    url = "https://www.cargurus.com/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action"
    logger.info(f"Starting to scrape CarGurus at {url}")
    
    car_data = scrape_cargurus(url, max_pages=3)
    
    if car_data:
        for car in car_data:
            logger.info(f"Car: {car}")
    else:
        logger.warning("No car data was collected.")
