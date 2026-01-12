import scraper
import sys

# specific failing URL
url = "https://www.makro.co.za/keter-mallorca-plastic-lounger/p/itm1043178e868c2?pid=LCEHACU2DEVQGEQJ&cmpid=product.share.pp&lid=LSTLCEHACU2DEVQGEQJ0FUPKA"

print(f"Testing URL: {url}")
try:
    price = scraper.get_price(url)
    print(f"Returned Price: {price}")
    if price and price != "Not Found" and price != "Invalid URL" and "Error" not in price:
        print("SUCCESS: Price found.")
    else:
        print("FAILURE: Price not found.")
except Exception as e:
    print(f"EXCEPTION: {e}")
