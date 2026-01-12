import time
import random
import re
import json
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

def clean_price(price_str):
    if not price_str:
        return "N/A"
    
    # If it's a status message (letters only) or error, return it as is
    if "Found" in price_str or "Error" in price_str or not any(char.isdigit() for char in price_str):
        return price_str

    # Otherwise, clean it up to be just numbers and decimals/commas
    clean = re.sub(r'[^\d.,]', '', price_str)
    return clean.strip()

def extract_price_from_text(text):
    """Fallback: Search for R xxx.xx patterns in text"""
    matches = re.findall(r'R\s?[\d,.]+\d', text)
    if matches:
        return matches[0]
    return None

def extract_from_jsonld(page):
    """Helper to extract price from JSON-LD structured data"""
    try:
        # Get all JSON-LD scripts
        structured_data_list = page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            return Array.from(scripts).map(s => s.innerText);
        }""")
        
        for sd_text in structured_data_list:
            try:
                data = json.loads(sd_text)
                
                # Helper to check a single dict for offers/price
                def check_product_node(node):
                    if node.get('@type') == 'Product' or node.get('@type') == 'http://schema.org/Product':
                        offers = node.get('offers')
                        if isinstance(offers, dict):
                            return offers.get('price')
                        elif isinstance(offers, list):
                            for offer in offers:
                                return offer.get('price')
                    return None

                # Case 1: Root is the Product
                if isinstance(data, dict):
                    p = check_product_node(data)
                    if p: return str(p)
                    
                    # Case 2: Graph array
                    if '@graph' in data and isinstance(data['@graph'], list):
                        for item in data['@graph']:
                            p = check_product_node(item)
                            if p: return str(p)

                # Case 3: Root is a list of objects
                elif isinstance(data, list):
                    for item in data:
                        p = check_product_node(item)
                        if p: return str(p)

            except:
                continue
    except:
        pass
    return None

def get_price(url):
    print(f"Scraping: {url}...")
    if not url or str(url).lower() == 'nan':
        return "Invalid URL"
        
    ua = UserAgent()
    is_makro = 'makro' in url.lower()
    
    # Makro requires headful mode to pass "Are you human?" checks
    # But user requested background execution. We will try headless with extra stealth.
    run_headless = True
    
    # Use fixed UA for Makro as it proved more stable in debugging
    final_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" if is_makro else ua.random

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=run_headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certifcate-errors',
                '--ignore-certificate-errors-spki-list',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu'
            ]
        )
        
        # Create context with random user agent and viewport
        context = browser.new_context(
            user_agent=final_ua,
            viewport={'width': 1920, 'height': 1080},
            locale='en-ZA',
            timezone_id='Africa/Johannesburg'
        )

        # Stealth: Remove navigator.webdriver property and add other mocks
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock window.chrome
            window.chrome = {
                runtime: {}
            };
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-ZA', 'en-US', 'en'],
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
        """)
        
        page = context.new_page()
        
        try:
            # Go to URL
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            
            # Anti-bot evasion: Simulate mouse movements
            if is_makro:
                # Check for blocking title immediately
                try:
                    page.wait_for_load_state('networkidle', timeout=5000)
                except: pass
                
                # Small delay to ensure page is stable
                time.sleep(1)

                try:
                    title = page.title().lower()
                    if "human" in title or "denied" in title or "just a moment" in title:
                        print("  Blocked by Makro security. Waiting for challenge to pass...")
                        # Wait for title to change or a specific element that indicates success
                        # Typically the title changes back to the product name or "Makro"
                        try:
                            page.wait_for_function("document.title.indexOf('human') === -1", timeout=20000)
                            print("  Challenge likely passed (title changed).")
                        except:
                            print("  Timeout waiting for challenge.")
                except Exception as title_error:
                    # If browser closed or other error, just log and continue to fallback
                    print(f"  Warning: Could not check title ({str(title_error)[:50]})...")
                
                try:
                    page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                    page.mouse.down()
                    time.sleep(0.2)
                    page.mouse.up()
                    time.sleep(random.uniform(2, 4))
                except: pass
            else:
                time.sleep(3)
            
            price = None
            found_via_selector = False
            
            # --- AMAZON ---
            if 'amazon' in url.lower():
                selectors = [
                    'span.a-price.a-text-price span.a-offscreen',
                    'span.a-price span.a-offscreen',
                    '#priceblock_ourprice',
                    '#priceblock_dealprice',
                    '.a-price .a-offscreen'
                ]
                for sel in selectors:
                    if page.locator(sel).count() > 0:
                        price = page.locator(sel).first.text_content()
                        found_via_selector = True
                        break

            # --- MAKRO ---
            elif 'makro' in url.lower():
                # Check for blocking title
                if "human" in page.title().lower() or "denied" in page.title().lower():
                    print("  Blocked by Makro security. Waiting for redirect...")
                    time.sleep(5) # Give it a moment to solve itself or redirect

                try:
                    page.wait_for_load_state('networkidle', timeout=15000)
                except: pass

                # 1. Try JSON-LD
                json_price = extract_from_jsonld(page)
                if json_price:
                    price = json_price
                    found_via_selector = True
                
                # 2. Try meta tag
                if not found_via_selector:
                    try:
                        price = page.locator('meta[property="product:price:amount"]').get_attribute('content')
                        if price: found_via_selector = True
                    except: pass
                
                # 3. Try selectors
                if not found_via_selector:
                    selectors = [
                        '.price', '.prod-price', '[data-test="product-price"]', 
                        '.mak-product-price', 'span[itemprop="price"]', 
                        'div[class*="price-container"] span', 'h1 + div span'
                    ]
                    for sel in selectors:
                        if page.locator(sel).count() > 0:
                            possible = page.locator(sel).first.text_content()
                            if any(char.isdigit() for char in possible):
                                price = possible
                                found_via_selector = True
                                break

            # --- TAKEALOT ---
            elif 'takealot' in url.lower():
                selectors = [
                    '.pdp-main-panel .buy-box-price', 
                    '[data-ref="buy-box-price"]',
                    '.price-container',
                    'div[class*="price"]' 
                ]
                for sel in selectors:
                    if page.locator(sel).count() > 0:
                        price = page.locator(sel).first.text_content()
                        if price and any(char.isdigit() for char in price):
                            found_via_selector = True
                            break

            # --- FALLBACK ---
            if not found_via_selector or not price:
                print("Selectors failed. Trying text search...")
                body_text = page.inner_text("body")
                extracted = extract_price_from_text(body_text)
                if extracted:
                    price = extracted
                else:
                    price = "Not Found"

            print(f"Result: {clean_price(price)}")
            return clean_price(price)
            
        except Exception as e:
            print(f"Error: {e}")
            return f"Error: {str(e)[:50]}"
        finally:
            browser.close()
