from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# not working due to JS 3/30/25
# Set up Selenium WebDriver
def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Scrape AutoTrader listings
def scrape_autotrader(url, max_pages=3):
    driver = setup_driver()
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cmp='inventoryListing']")))

    all_cars = []
    
    for page in range(1, max_pages + 1):
        print(f"Scraping page {page}...")

        # Wait for listings to be present
        listings = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-cmp='inventoryListing']")))
        print(f"Found {len(listings)} listings on page {page}")
        
        for listing in listings:
            try:
                car = {}
                
                # Get car title
                car["title"] = listing.find_element(By.CSS_SELECTOR, "a[data-cmp='link'] h2[data-cmp='subheading']").text
                
                # Get car price
                car["price"] = listing.find_element(By.CSS_SELECTOR, "div[data-cmp='pricing'] div[data-cmp='firstPrice']").text
                
                # Get car mileage
                car["mileage"] = listing.find_element(By.CSS_SELECTOR, "div[data-cmp='mileageSpecification']").text
                
                # Get car location (dealer info)
                car["location"] = listing.find_element(By.CSS_SELECTOR, "div[data-cmp='listing-footer'] div.text-left div.text-subdued").text
                
                all_cars.append(car)
            
            except Exception as e:
                print(f"Error extracting car details: {e}")
                continue

        # Try to click next page button (if present)
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a[aria-label='Next Page']")
            next_button.click()
            time.sleep(3)  # Wait for the next page to load
        except Exception as e:
            print("No more pages or next button not found.")
            break
    
    driver.quit()
    return all_cars

if __name__ == "__main__":
    url = "https://www.autotrader.com/cars-for-sale/all-cars"
    car_data = scrape_autotrader(url, max_pages=3)
    
    if car_data:
        for car in car_data:
            print(car)
    else:
        print("No car data was collected.")
