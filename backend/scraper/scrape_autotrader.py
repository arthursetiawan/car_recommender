import requests
from bs4 import BeautifulSoup

URL = "https://www.autotrader.com/cars-for-sale/edmonds-wa"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def scrape_autotrader():
    response = requests.get(URL, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        cars = []
        for listing in soup.find_all("div", class_="inventory-listing"):  # Update class name as needed
            title_tag = listing.find("h2", class_="title")
            title = title_tag.text.strip() if title_tag else "Unknown"
            
            price_tag = listing.find("span", class_="first-price")
            price = price_tag.text.strip() if price_tag else "N/A"
            
            mileage_tag = listing.find("div", class_="text-bold")  # Mileage info
            mileage = mileage_tag.text.strip() if mileage_tag else "N/A"
            
            engine_tag = listing.find("div", class_="engine")  # Engine specs
            engine = engine_tag.text.strip() if engine_tag else "N/A"
            
            features_tag = listing.find("ul", class_="list")  # Features list
            features = ", ".join([li.text.strip() for li in features_tag.find_all("li")]) if features_tag else "N/A"
            
            location_tag = listing.find("div", class_="dealer-address")
            location = location_tag.text.strip() if location_tag else "N/A"
            
            cars.append({
                "title": title,
                "price": price,
                "mileage": mileage,
                "engine": engine,
                "features": features,
                "location": location
            })
        
        return cars
    
    return None

if __name__ == "__main__":
    car_data = scrape_autotrader()
    if car_data:
        for car in car_data:
            print(car)
    else:
        print("Failed to retrieve data.")
