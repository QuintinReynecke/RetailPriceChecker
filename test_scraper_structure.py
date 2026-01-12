import scraper
import sys

# Mocking playwright to avoid launching browser during simple structure test if possible,
# but since the code imports it inside the function, we can just call the function.
# However, without internet, it will fail to reach the URL.
# We just want to see if it returns the dict with "Error" or similar, 
# and not crash due to syntax or variable name errors.

print("Testing scraper structure...")

try:
    # We use a dummy URL. It will fail to connect but should return the dict with error.
    # If we used a real URL, it would try to connect.
    url = "http://example.com" 
    
    print(f"Calling scrape_product with {url}...")
    result = scraper.scrape_product(url)
    
    print("\nResult received:")
    print(result)
    
    expected_keys = [
        "Product Code", "Description", "Link", "PLID", "RSP", "Original Price", 
        "Seller", "Stock Availability", "Rating", "Review Count", 
        "Other Seller", "Other Price", "Error"
    ]
    
    missing_keys = [key for key in expected_keys if key not in result]
    
    if missing_keys:
        print(f"\nFAILED: Missing keys: {missing_keys}")
        sys.exit(1)
    else:
        print("\nSUCCESS: All keys present.")
        
except Exception as e:
    print(f"\nCRASHED: {e}")
    sys.exit(1)
