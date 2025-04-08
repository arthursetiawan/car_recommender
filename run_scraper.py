import subprocess
import logging
import os
from backend.scraper_selenium.scrape_carscom import scrape_cars_com
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

if __name__ == "__main__":
    cars_data = scrape_cars_com("https://www.cars.com/shopping/results/", max_pages=1)

    csv_file = "data/cars_com_data.csv"
    
    if cars_data:
        df = pd.DataFrame(cars_data)

        # Append data to CSV (create if doesn't exist)
        df.to_csv(csv_file, mode="a", index=False, encoding="utf-8", header=not pd.io.common.file_exists(csv_file))

        logger.info(f"Data successfully appended to {csv_file}")
