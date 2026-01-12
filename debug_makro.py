from playwright.sync_api import sync_playwright
import time
import random

url = "https://www.makro.co.za/keter-mallorca-plastic-lounger/p/itm1043178e868c2?pid=LCEHACU2DEVQGEQJ&cmpid=product.share.pp&lid=LSTLCEHACU2DEVQGEQJ0FUPKA"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled', '--start-maximized'])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080},
        locale='en-ZA',
        timezone_id='Africa/Johannesburg'
    )
    
    # Stealth scripts
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-ZA', 'en-US', 'en'],
        });
    """)

    page = context.new_page()
    print("Navigating...")
    page.goto(url)
    
    # Human-like interaction
    print("Simulating human behavior...")
    page.mouse.move(random.randint(100, 500), random.randint(100, 500))
    time.sleep(1)
    
    print("Checking title...")
    print(f"Title: {page.title()}")
    
    if "human" in page.title().lower() or "denied" in page.title().lower():
        print("Still blocked? Waiting...")
        time.sleep(10)
        print(f"Title after wait: {page.title()}")

    print("Saving HTML...")
    with open("makro_debug.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    
    print("Saving Screenshot...")
    page.screenshot(path="makro_debug.png")
    
    print("Done.")
    browser.close()
