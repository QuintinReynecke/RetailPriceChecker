from playwright.sync_api import sync_playwright
import time

url = "https://www.takealot.com/xiaomi-smart-air-purifier-4-compact-eu/PLID91193746"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    print(f"Navigating to {url}...")
    page.goto(url, wait_until='networkidle')
    time.sleep(5)
    
    content = page.content()
    
    # Save full HTML for review
    with open("takealot_debug.html", "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Saved HTML to takealot_debug.html")
    
    # Check if we can find the specific class the user mentioned
    try:
        # Search for any element with class containing 'list-price'
        elements = page.locator('[class*="list-price"]').all()
        print(f"Found {len(elements)} elements with class containing 'list-price'")
        for i, el in enumerate(elements):
            print(f"Element {i}: Tag={el.evaluate('el => el.tagName')}, Text={el.text_content()}, Class={el.get_attribute('class')}")
            
        # Search for text '2,199' to see where it lives
        print("\nSearching for '2,199'...")
        price_els = page.get_by_text("2,199").all()
        for i, el in enumerate(price_els):
             print(f"Price Match {i}: Tag={el.evaluate('el => el.tagName')}, Class={el.get_attribute('class')}, Parent Class={el.locator('..').get_attribute('class')}")

    except Exception as e:
        print(f"Error inspecting elements: {e}")

    browser.close()
