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
        
        # Example: Extracting car listings
        cars = []
        for listing in soup.find_all("div", class_="listing-search-results-item"):  # Update class name as needed
            title_tag = listing.find("h4", class_="WoAzt dzuXc _titleText_4bb51_15")
            title = title_tag.text.strip() if title_tag else "Unknown"
            price = listing.find("span", class_="price").text.strip() if listing.find("span", class_="price") else "N/A"
  
            mileage = listing.find("span", class_="mileage").text.strip() if listing.find("span", class_="mileage") else "N/A"
            
            cars.append({
                "title": title,
                "price": price,
                "mileage": mileage
            })
        
        return cars
    
    return None

if __name__ == "__main__":
    car_data = scrape_cars()
    if car_data:
        for car in car_data:
            print(car)
    else:
        print("Failed to retrieve data.")
