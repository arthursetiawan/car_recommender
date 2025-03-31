import unittest
from backend.scraper.scrape_autotrader import scrape_autotrader
from backend.scraper.scrape_cargurus import scrape_cargurus
from backend.scraper.scrape_carscom import scrape_cars_com

class TestScraper(unittest.TestCase):
    def test_scrape_cars(self):
        # data = scrape_cargurus('https://www.cargurus.com/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action?sourceContext=carGurusHomePageModel&entitySelectingHelper.selectedEntity=d306&zip=98037')
        data = scrape_cars_com()
        self.assertIsNotNone(data)

if __name__ == "__main__":
    unittest.main()
