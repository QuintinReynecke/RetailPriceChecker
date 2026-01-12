import scraper
import sys

urls = [
    "https://www.amazon.co.za/Belkin-Thunderbolt-Display-Compatible-Delivery/dp/B09MR14ZWT/",
    "https://www.amazon.co.za/Belkin-Delivery-Transfer-Multiport-Chromebook/dp/B0FVYC8H5J/"
]

print("Starting Amazon Scraper Verification...")

for url in urls:
    print(f"\n--------------------------------------------------")
    print(f"Testing URL: {url}")
    try:
        data = scraper.scrape_product(url)
        print("Scraped Data:")
        for k, v in data.items():
            print(f"  {k}: {v}")
            
        if data["Review Count"] != "N/A":
            print(f"SUCCESS: Review Count found: {data['Review Count']}")
        else:
            print("FAILURE: Review Count is N/A")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")
