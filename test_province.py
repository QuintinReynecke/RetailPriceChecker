import scraper
import sys

# Test URL provided by user
url = "https://www.takealot.com/eufy-s1-pro-smart-robot-vacuum-cleaner-and-mop/PLID97003327"

print(f"Testing URL: {url}")
try:
    data = scraper.scrape_product(url)
    print("\n--- Scraped Data ---")
    for k, v in data.items():
        print(f"{k}: {v}")
    
    if "Province" in data:
        print(f"\nProvince: {data['Province']}")
        if data['Province'] == "N/A":
             print("WARNING: Province is N/A. Check if the product page actually has shipping info.")
    else:
        print("\nERROR: 'Province' key missing from result.")

except Exception as e:
    print(f"Error: {e}")
