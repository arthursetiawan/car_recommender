import subprocess
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Define the scraper script path
SCRAPER_SCRIPT = os.path.join("backend", "scraper_selenium", "scrape_carscom.py")

def run_scraper():
    """Run the scrape_carscom.py script and log its output."""
    if not os.path.exists(SCRAPER_SCRIPT):
        logger.error(f"Scraper script not found at: {SCRAPER_SCRIPT}")
        return

    try:
        logger.info(f"Running scraper: {SCRAPER_SCRIPT}")
        result = subprocess.run(["python", SCRAPER_SCRIPT], capture_output=True, text=True, check=True)

        # Log the output
        logger.info(f"Scraper Output:\n{result.stdout}")
        
        # Log any errors
        if result.stderr:
            logger.error(f"Scraper Error:\n{result.stderr}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Scraper failed with error:\n{e.stderr}")

if __name__ == "__main__":
    run_scraper()
