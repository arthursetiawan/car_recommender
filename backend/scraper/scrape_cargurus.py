import requests
from bs4 import BeautifulSoup

URL = "https://www.cargurus.com/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def scrape_cars():
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        # Extract car details
        return soup.prettify()
    return None

print(scrape_cars())
