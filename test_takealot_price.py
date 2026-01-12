import scraper
import sys

# Test URL provided by user
url = "https://www.takealot.com/proline-v116-11-6-inch-laptop-intel-celeron-n4020-4gb-ram-128gb-/PLID98514871"

print(f"Testing URL: {url}")
try:
    data = scraper.scrape_product(url)
    print("\n--- Scraped Data ---")
    for k, v in data.items():
        print(f"{k}: {v}")
    
    if "Original Price" in data:
        print(f"\nOriginal Price: {data['Original Price']}")
        if data['Original Price'] == "N/A":
             print("WARNING: Original Price is N/A. Check if the product page actually has a list/old price.")
    else:
        print("\nERROR: 'Original Price' key missing from result.")

except Exception as e:
    print(f"Error: {e}")
