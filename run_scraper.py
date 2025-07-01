import subprocess
import logging
import os
from backend.scraper_selenium.scrape_carscom import scrape_cars_com
from backend.utils import upload_to_supabase
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

if __name__ == "__main__":
    logger.info('Scraping cars.com')
    cars_data = scrape_cars_com("https://www.cars.com/shopping/results/", max_pages=20)
    
    if cars_data:
        df = pd.DataFrame(cars_data)

        # Upload to Supabase
        logger.info('Uploading to Supabase')
        upload_to_supabase(df)
