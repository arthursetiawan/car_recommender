import logging
import re
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Function to split title into year, model, and trim
def parse_title(title):
    match = re.match(r"(\d{4})\s+([\w\s-]+?)(?:\s+([A-Z]+.*))?$", title)
    if match:
        year, model, trim = match.groups()
        return {
            "year": year.strip(),
            "model": model.strip(),
            "trim": trim.strip() if trim else "Base"
        }
    return {"year": "Unknown", "model": title, "trim": "Unknown"}

# Scrape Cars.com listings (max 10 pages)
def scrape_cars_com(base_url, max_pages=100):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    all_cars = []
    
    for page in range(1, max_pages + 1):
        url = f"{base_url}?page={page}"
        driver.get(url)
        time.sleep(5)  # Wait for page to load
        
        listings = driver.find_elements(By.CSS_SELECTOR, "div.vehicle-card")
        logger.info(f"Found {len(listings)} listings on page {page}")
        
        for listing in listings:
            try:
                car = {}
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Title
                title = listing.find_element(By.CSS_SELECTOR, "h2.title").text.strip()
                parsed_title = parse_title(title)

                car["year"] = parsed_title["year"]
                car["model"] = parsed_title["model"]
                car["trim"] = parsed_title["trim"]

                # Price
                car["price"] = listing.find_element(By.CSS_SELECTOR, "span.primary-price").text.strip()

                # Mileage
                try:
                    car["mileage"] = listing.find_element(By.CSS_SELECTOR, "div.mileage").text.strip()
                except:
                    car["mileage"] = "N/A"

                # Dealership name
                try:
                    car["dealer_name"] = listing.find_element(By.CSS_SELECTOR, "div.dealer-name").text.strip()
                except:
                    car["dealer_name"] = "N/A"

                # Get city & state (miles from user)
                try:
                    car["city_state"] = listing.find_element(By.CSS_SELECTOR, "div[data-qa='miles-from-user']").text.strip()
                except:
                    car["city_state"] = "N/A"

                # Get finance estimate
                try:
                    finance_element = listing.find_element(By.CSS_SELECTOR, "spark-button.monthly-payment-est-link span")
                    car["finance_estimate"] = finance_element.text.strip()
                except:
                    car["finance_estimate"] = "N/A"

                # Timestamp
                car["scraped_at"] = timestamp

                all_cars.append(car)

            except Exception as e:
                logger.error(f"Error extracting car details: {e}")
                continue

    driver.quit()
    logger.info("Scraping completed.")
    return all_cars

if __name__ == "__main__":
    url = "https://www.cars.com/shopping/results/"
    csv_file = "../../data/cars_com_data.csv"
    
    # Scrape data
    cars_data = scrape_cars_com(url, max_pages=100)
    
    if cars_data:
        df = pd.DataFrame(cars_data)

        # Append data to CSV (create if doesn't exist)
        df.to_csv(csv_file, mode="a", index=False, encoding="utf-8", header=not pd.io.common.file_exists(csv_file))

        logger.info(f"Data successfully appended to {csv_file}")
    else:
        logger.warning("No data collected.")
