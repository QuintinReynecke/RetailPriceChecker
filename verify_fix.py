import scraper
import sys

# specific URL provided by user
url = "https://www.takealot.com/xiaomi-smart-air-purifier-4-compact-eu/PLID91193746"

print(f"Testing scraping for: {url}")
try:
    results = scraper.scrape_products_batch([url])
    if results:
        r = results[0]
        print("\n--- Result ---")
        print(f"Product: {r.get('Description')}")
        print(f"Current Price (RSP): {r.get('RSP')}")
        print(f"Original Price: {r.get('Original Price')}")
        print(f"Stock: {r.get('Stock Availability')}")
        print(f"Seller: {r.get('Seller')}")
    else:
        print("No results returned.")
except Exception as e:
    print(f"Error: {e}")