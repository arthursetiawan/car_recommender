from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import pandas as pd

#MAX PAGES SET TO 5
def scrape_cars_com(base_url, max_pages=10):
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
        
        for listing in listings:
            try:
                title = listing.find_element(By.CSS_SELECTOR, "h2.title").text.strip()
                price = listing.find_element(By.CSS_SELECTOR, "span.primary-price").text.strip()
                mileage = listing.find_element(By.CSS_SELECTOR, "div. mileage").text.strip() if listing.find_elements(By.CSS_SELECTOR, "div.mileage") else "N/A"
                location = listing.find_element(By.CSS_SELECTOR, "div.dealer-name").text.strip() if listing.find_elements(By.CSS_SELECTOR, "div.dealer-name") else "N/A"
                
                car = {
                    "title": title,
                    "price": price,
                    "mileage": mileage,
                    "location": location
                }
                all_cars.append(car)
            except Exception as e:
                print(f"Error extracting data: {e}")
    
    driver.quit()
    return all_cars

if __name__ == "__main__":
    url = "https://www.cars.com/shopping/results/"
    cars_data = scrape_cars_com(url, max_pages=10)
    
    if cars_data:
        df = pd.DataFrame(cars_data)
        df.to_csv("results/cars_com_data.csv", index=False, encoding="utf-8")
        print("Data saved to cars_com_data.csv")
    else:
        print("No data collected.")
