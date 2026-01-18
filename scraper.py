import time
import random
import re
import json
import asyncio
import sys
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

def clean_price(price_str):
    if not price_str:
        return "N/A"
    
    # If it's a status message (letters only) or error, return it as is
    if "Found" in price_str or "Error" in price_str or "Invalid" in price_str:
        return price_str

    # Clean up R currency, commas, etc
    clean = re.sub(r'[^\d.,]', '', str(price_str))
    return clean.strip()

def extract_price_from_text(text):
    """Fallback: Search for R xxx.xx patterns in text"""
    matches = re.findall(r'R\s?[\d,.]+\d', text)
    if matches:
        return matches[0]
    return None

def extract_from_jsonld(page):
    """Helper to extract product data from JSON-LD structured data"""
    data_extracted = {}
    try:
        # Get all JSON-LD scripts
        structured_data_list = page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            return Array.from(scripts).map(s => s.innerText);
        }""")
        
        for sd_text in structured_data_list:
            try:
                data = json.loads(sd_text)
                
                # Helper to process a product node
                def process_product_node(node):
                    extracted = {}
                    if node.get('@type') in ['Product', 'http://schema.org/Product']:
                        if 'name' in node: extracted['Description'] = node['name']
                        if 'sku' in node: extracted['Product Code'] = node['sku']
                        if 'productID' in node: extracted['PLID'] = node['productID']
                        
                        # Offers
                        offers = node.get('offers')
                        if isinstance(offers, dict):
                            if 'price' in offers: extracted['RSP'] = str(offers['price'])
                            if 'priceCurrency' in offers: extracted['Currency'] = offers['priceCurrency']
                            if 'availability' in offers: extracted['Stock Availability'] = offers['availability'].split('/')[-1]
                            if 'seller' in offers:
                                seller = offers['seller']
                                if isinstance(seller, dict) and 'name' in seller:
                                    extracted['Seller'] = seller['name']
                        elif isinstance(offers, list) and len(offers) > 0:
                            # Take first offer
                            first_offer = offers[0]
                            if 'price' in first_offer: extracted['RSP'] = str(first_offer['price'])
                            if 'availability' in first_offer: extracted['Stock Availability'] = first_offer['availability'].split('/')[-1]
                            if 'seller' in first_offer:
                                seller = first_offer['seller']
                                if isinstance(seller, dict) and 'name' in seller:
                                    extracted['Seller'] = seller['name']

                        # Ratings
                        if 'aggregateRating' in node:
                            rating = node['aggregateRating']
                            if isinstance(rating, dict):
                                if 'ratingValue' in rating: extracted['Rating'] = str(rating['ratingValue'])
                                if 'reviewCount' in rating: extracted['Review Count'] = str(rating['reviewCount'])
                        
                        return extracted
                    return None

                # Traverse JSON-LD structure
                found_data = None
                if isinstance(data, dict):
                    found_data = process_product_node(data)
                    if not found_data and '@graph' in data and isinstance(data['@graph'], list):
                        for item in data['@graph']:
                            found_data = process_product_node(item)
                            if found_data: break
                elif isinstance(data, list):
                    for item in data:
                        found_data = process_product_node(item)
                        if found_data: break
                
                if found_data:
                    data_extracted.update(found_data)

            except:
                continue
    except:
        pass
    return data_extracted

def extract_from_takealot_next_data(page):
    """Helper to extract Takealot data from __NEXT_DATA__ or similar state blobs"""
    data_extracted = {}
    try:
        # Try to find the __NEXT_DATA__ script
        next_data_json = page.evaluate("""() => {
            const script = document.getElementById('__NEXT_DATA__');
            if (script) return JSON.parse(script.innerText);
            return null;
        }""")

        if next_data_json:
            try:
                # Helper to find dictionary with specific keys recursively
                def find_key(obj, key):
                    if isinstance(obj, dict):
                        if key in obj: return obj[key]
                        for k, v in obj.items():
                            found = find_key(v, key)
                            if found: return found
                    elif isinstance(obj, list):
                        for item in obj:
                            found = find_key(item, key)
                            if found: return found
                    return None
                    
                # Search for 'product' or 'reviews' keys anywhere in the props
                props = next_data_json.get('props', {})
                
                # 1. Try to find product info
                product_data = find_key(props, 'product')
                if not product_data:
                     # Try finding something with 'buybox' which implies product data
                    buybox_parent = find_key(props, 'buybox')
                    if buybox_parent:
                         # Use the parent of buybox as product data if possible, or the dict itself if it contains title
                         pass # Hard to reconstruct parent from recursive return, assume standard paths failed if we are here.

                if product_data:
                     if 'title' in product_data: data_extracted['Description'] = product_data['title']
                     if 'core' in product_data and 'title' in product_data['core']: data_extracted['Description'] = product_data['core']['title']
                     
                     buybox = product_data.get('buybox', {})
                     if buybox:
                        if 'prettyPrice' in buybox: data_extracted['RSP'] = buybox['prettyPrice']
                        elif 'price' in buybox: data_extracted['RSP'] = str(buybox['price'])
                        
                        # Original Price / List Price
                        if 'prices' in buybox and isinstance(buybox['prices'], list):
                             # Often the list price is the max price in the list or explicitly labeled
                             # But usually 'prettyOldPrice' or similar is easier if available
                             pass

                        if 'prettyOldPrice' in buybox and buybox['prettyOldPrice']:
                            data_extracted['Original Price'] = buybox['prettyOldPrice']
                        elif 'oldPrice' in buybox and buybox['oldPrice']:
                            data_extracted['Original Price'] = str(buybox['oldPrice'])
                        
                        if 'stockAvailability' in buybox: 
                            status = buybox['stockAvailability'].get('status', '')
                            if status: data_extracted['Stock Availability'] = status
                        
                        if 'seller' in buybox:
                            data_extracted['Seller'] = buybox['seller'].get('name')
                            
                     # Reviews in product object
                     reviews = product_data.get('reviews', {})
                     if reviews:
                        if 'starRating' in reviews: data_extracted['Rating'] = str(reviews['starRating'])
                        if 'reviewCount' in reviews: data_extracted['Review Count'] = str(reviews['reviewCount'])

            except Exception as e:
                print(f"Error parsing Takealot NEXT_DATA content: {e}")
                
    except Exception as e:
        # print(f"Error finding Takealot NEXT_DATA: {e}")
        pass
        
    return data_extracted

def scrape_products_batch(urls, progress_callback=None):
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    results = []
    ua = UserAgent()
    
    # Check if any URL is Makro to decide on the global UserAgent strategy
    # Makro is stricter, so if we have Makro links, we might want to use the specific UA for everything 
    # or switch contexts. For simplicity in batching, let's use the Makro-friendly UA for all if any Makro exists,
    # as it mimics a real Windows/Chrome user which is generally good for others too.
    has_makro = any('makro' in u.lower() for u in urls)
    
    final_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" 
    if not has_makro:
        final_ua = ua.random

    run_headless = True
    
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
        
        context = browser.new_context(
            user_agent=final_ua,
            viewport={'width': 1920, 'height': 1080},
            locale='en-ZA',
            timezone_id='Africa/Johannesburg'
        )

        # Stealth scripts
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5], });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-ZA', 'en-US', 'en'], });
        """)
        
        page = context.new_page()
        
        for i, url in enumerate(urls):
            if progress_callback:
                progress_callback(i, url)
                
            print(f"Scraping ({i+1}/{len(urls)}): {url}...")
            
            result = {
                "Product Code": "N/A",
                "Description": "N/A",
                "Link": url,
                "PLID": "N/A",
                "RSP": "N/A",
                "Original Price": "N/A",
                "Seller": "N/A",
                "Stock Availability": "N/A",
                "Province": "N/A",
                "Rating": "N/A",
                "Review Count": "N/A",
                "Other Seller": "N/A",
                "Other Price": "N/A",
                "Error": "None"
            }

            if not url or str(url).lower() == 'nan':
                result["Error"] = "Invalid URL"
                results.append(result)
                continue
            
            is_makro = 'makro' in url.lower()
            
            try:
                page.goto(url, timeout=60000, wait_until='domcontentloaded')
                
                # Anti-bot logic for Makro
                if is_makro:
                    try:
                        page.wait_for_load_state('networkidle', timeout=5000)
                        time.sleep(1)
                        if "human" in page.title().lower() or "denied" in page.title().lower():
                            print("  Blocked by Makro security. Waiting...")
                            try:
                                page.wait_for_function("document.title.indexOf('human') === -1", timeout=20000)
                            except: pass
                    except: pass
                    
                    # Mouse movement simulation
                    try:
                        page.mouse.move(random.randint(100, 500), random.randint(100, 500))
                    except: pass
                else:
                    time.sleep(3) # Generic wait for others

                # --- 1. Extract from JSON-LD first (Most reliable) ---
                json_data = extract_from_jsonld(page)
                result.update(json_data)

                # --- 2. Site-Specific Fallbacks and Additional Data ---
                
                # --- AMAZON ---
                if 'amazon' in url.lower():
                    # Ensure page is loaded (Amazon can be slow/heavy)
                    try:
                        page.wait_for_selector('#productTitle', timeout=5000)
                    except: pass

                    # Title
                    if result["Description"] == "N/A":
                        if page.locator('#productTitle').count() > 0:
                            result["Description"] = page.locator('#productTitle').first.text_content().strip()
                        elif page.locator('h1').count() > 0:
                            result["Description"] = page.locator('h1').first.text_content().strip()
                        else:
                            result["Description"] = page.title().strip()
                    
                    # Price - Focused on "Core Price Display" (Standard for Desktop)
                    html_price = None
                    
                    # The main price block usually has ID 'corePriceDisplay_desktop_feature_div' or 'corePrice_desktop'
                    core_price_selectors = [
                        '#corePriceDisplay_desktop_feature_div',
                        '#corePrice_desktop',
                        '#apex_desktop',
                        '.priceToPay' # Fallback container
                    ]
                    
                    for container_sel in core_price_selectors:
                        container = page.locator(container_sel).first
                        if container.count() > 0:
                            # 1. Look for "Price To Pay" class (Used for Deals and Regular)
                            price_to_pay = container.locator('.priceToPay').first
                            if price_to_pay.count() > 0:
                                # Try a-offscreen first (hidden accessible text)
                                offscreen = price_to_pay.locator('.a-offscreen').first
                                if offscreen.count() > 0:
                                    txt = offscreen.text_content().strip()
                                    if txt and 'R' in txt:
                                        html_price = txt
                                        break
                                
                                # Try visible text components (Whole + Fraction)
                                whole = price_to_pay.locator('.a-price-whole').first
                                fraction = price_to_pay.locator('.a-price-fraction').first
                                if whole.count() > 0:
                                    w_txt = whole.text_content().strip()
                                    f_txt = fraction.text_content().strip() if fraction.count() > 0 else "00"
                                    # Handle "5 689" -> "5689" later in clean_price, just join here
                                    html_price = f"R {w_txt}.{f_txt}"
                                    break
                            
                            # 2. Look for Apex Price (Deal specific sometimes)
                            apex = container.locator('.apexPriceToPay .a-offscreen').first
                            if apex.count() > 0:
                                html_price = apex.text_content()
                                break
                            
                            # 3. Generic a-price that is NOT a text price (List Price)
                            # We grab the first one that is visible
                            prices = container.locator('.a-price:not(.a-text-price)').all()
                            for p in prices:
                                if p.is_visible():
                                    offscreen = p.locator('.a-offscreen').first
                                    if offscreen.count() > 0:
                                        html_price = offscreen.text_content()
                                        break
                                    # Fallback to text
                                    txt = p.text_content().strip()
                                    if txt and 'R' in txt:
                                        html_price = txt
                                        break
                            if html_price:
                                break
                    
                    # Fallback if Core Price container failed (e.g. older layouts)
                    if not html_price:
                         fallback_selectors = ['#priceblock_ourprice', '#priceblock_dealprice', '.a-price.a-text-price.a-size-medium .a-offscreen']
                         for sel in fallback_selectors:
                             if page.locator(sel).count() > 0:
                                prices = page.locator(sel).all()
                                for p in prices:
                                    if p.is_visible():
                                        html_price = p.text_content()
                                        break
                                if html_price:
                                    break
                    
                    if html_price:
                        result["RSP"] = html_price

                    # Original Price (List Price / Was Price)
                    if result["Original Price"] == "N/A":
                        # We search specifically for the "basisPrice" or "a-text-price" often found in the core display
                        op_selectors = [
                            '#corePriceDisplay_desktop_feature_div .a-text-price .a-offscreen',
                            '#corePrice_desktop .a-text-price .a-offscreen',
                            '.basisPrice .a-offscreen',
                            'span[data-a-strike="true"]',
                            '.a-price.a-text-price .a-offscreen'
                        ]
                        for sel in op_selectors:
                             if page.locator(sel).count() > 0:
                                candidates = page.locator(sel).all()
                                for c in candidates:
                                    # Check visibility of parent wrapper usually
                                    parent = c.locator('..')
                                    # We don't strict check parent visibility here as it sometimes fails for strike-throughs
                                    # but we DO check if the value is different from RSP
                                    
                                    txt = c.text_content().strip()
                                    if txt and 'R' in txt:
                                        cleaned_op = clean_price(txt)
                                        cleaned_rsp = clean_price(result["RSP"])
                                        
                                        # Strict check: Must be different from RSP and valid
                                        if cleaned_op and cleaned_rsp and cleaned_op != cleaned_rsp:
                                            result["Original Price"] = txt
                                            break
                                if result["Original Price"] != "N/A":
                                    break

                    # Seller
                    if result["Seller"] == "N/A":
                        seller_selectors = ['#merchant-info', '#sellerProfileTriggerId', 'div[tabular-attribute-name="Sold by"]', '.offer-display-feature-text-message']
                        for sel in seller_selectors:
                            if page.locator(sel).count() > 0:
                                text = page.locator(sel).first.text_content().strip()
                                text = text.replace("Sold by", "").strip()
                                if "fulfilled by" in text.lower():
                                    text = text.split("fulfilled by")[0].strip()
                                result["Seller"] = text
                                break
                        
                        if result["Seller"] == "N/A":
                            result["Seller"] = "Amazon"
                    
                    # Stock
                    if result["Stock Availability"] == "N/A":
                        if page.locator('#availability').count() > 0:
                            result["Stock Availability"] = page.locator('#availability').first.text_content().strip()
                    
                    # Rating & Reviews
                    if result["Rating"] == "N/A":
                        if page.locator('span[data-hook="rating-out-of-text"]').count() > 0:
                            result["Rating"] = page.locator('span[data-hook="rating-out-of-text"]').first.text_content()
                        elif page.locator('.a-icon-star').count() > 0:
                            result["Rating"] = page.locator('.a-icon-star').first.text_content()
                    
                    if result["Review Count"] == "N/A":
                        if page.locator('#acrCustomerReviewText').count() > 0:
                            result["Review Count"] = page.locator('#acrCustomerReviewText').first.text_content()
                        elif page.locator('span[data-hook="total-review-count"]').count() > 0:
                            result["Review Count"] = page.locator('span[data-hook="total-review-count"]').first.text_content()
                        else:
                            try:
                                candidates = page.get_by_text(re.compile(r'\d[\d,]*\s+(global\s+)?(ratings|reviews)', re.IGNORECASE)).all()
                                for c in candidates:
                                    text = c.text_content().strip()
                                    match = re.search(r'(\d[\d,]*)\s+(?:global\s+|customer\s+)?(?:ratings|reviews)', text, re.IGNORECASE)
                                    if match:
                                        result["Review Count"] = match.group(1)
                                        break
                            except: pass

                    # ASIN / Product Code
                    try:
                        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
                        if asin_match:
                            result["Product Code"] = asin_match.group(1)
                        elif page.locator('#ASIN').count() > 0:
                             result["Product Code"] = page.locator('#ASIN').get_attribute('value')
                    except: pass

                # --- MAKRO ---
                elif 'makro' in url.lower():
                    # Title
                    if result["Description"] == "N/A":
                        if page.locator('h1').count() > 0:
                            result["Description"] = page.locator('h1').first.text_content().strip()

                    # Price (if JSON failed)
                    if result["RSP"] == "N/A":
                        selectors = ['.price', '.prod-price', '[data-test="product-price"]', 'div[class*="price"]']
                        for sel in selectors:
                            if page.locator(sel).count() > 0:
                                text = page.locator(sel).first.text_content()
                                if any(char.isdigit() for char in text):
                                    result["RSP"] = text
                                    break
                    
                    # Seller
                    if result["Seller"] == "N/A":
                        if page.locator('#sellerName').count() > 0:
                            result["Seller"] = page.locator('#sellerName').first.text_content().strip()
                    
                    # Stock (Inferred)
                    if result["Stock Availability"] == "N/A":
                        text = page.inner_text('body').lower()
                        if "out of stock" in text or "sold out" in text:
                            result["Stock Availability"] = "Out of Stock"
                        elif "add to cart" in text:
                            result["Stock Availability"] = "In Stock"

                # --- TAKEALOT ---
                elif 'takealot' in url.lower():
                    # Scroll to trigger lazy loading
                    try:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1)
                    except: pass
    
                    # Product Code from URL (Takealot specific request)
                    try:
                        clean_url = url.split('?')[0]
                        # Get last part of URL as code
                        code = clean_url.rstrip('/').split('/')[-1]
                        result["Product Code"] = code
                        result["PLID"] = code
                    except: pass
                    
                    # Try hidden NEXT_DATA JSON first (Most detailed)
                    next_data = extract_from_takealot_next_data(page)
                    if next_data:
                        result.update(next_data)
    
                    # Title
                    if result["Description"] == "N/A":
                        if page.locator('h1').count() > 0:
                            result["Description"] = page.locator('h1').first.text_content().strip()
                    
                    # --- SCOPED SEARCH FOR PRICES ---
                    # Define the main product container to avoid scanning related products/footer
                    product_container = page.locator('.pdp-main-panel').first
                    if product_container.count() == 0:
                        # Fallback to a wider selection if main panel class changes, but try to stay above tabs/related
                        product_container = page.locator('.pdp-body').first 
                    
                    search_scope = product_container if product_container.count() > 0 else page
    
                    # Price
                    if result["RSP"] == "N/A":
                        selectors = ['.buy-box-price', '[data-ref="buy-box-price"]', '.price-container', 'div[class*="price"]']
                        for sel in selectors:
                            if search_scope.locator(sel).count() > 0:
                                result["RSP"] = search_scope.locator(sel).first.text_content()
                                break
                    
                    # Original Price (List Price)
                    # FORCE CHECK HTML to match user visual expectation (overwriting JSON if found)
                    html_original_price = None
                    
                    # Selectors for the crossed-out list price (Relative to search_scope)
                    op_selectors = ['.buy-box-old-price', '[data-ref="buy-box-list-price"]', '.list-price', 'div[class*="list-price"]']
                    for sel in op_selectors:
                        if search_scope.locator(sel).count() > 0:
                            # Use inner_text() to avoid hidden metadata
                            raw_text = search_scope.locator(sel).first.inner_text().strip()
                            
                            # Clean potential duplication (e.g. "R 4,9994999") by extracting the first valid price pattern
                            match = re.search(r'R\s?[\d,.]+', raw_text)
                            if match:
                                html_original_price = match.group(0)
                            else:
                                html_original_price = raw_text
                            break
                    
                    # Fallback text search if selector fails (e.g., "List price is R 4,999")
                    # CRITICAL: Only search inside the product container to avoid Related Products
                    if not html_original_price:
                        try:
                            # Look for text containing "List price" or "Was" near the price
                            list_price_els = search_scope.get_by_text(re.compile(r'List price|Was', re.IGNORECASE)).all()
                            for el in list_price_els:
                                text = el.text_content()
                                # Extract price pattern R xxx
                                price_match = re.search(r'R\s?[\d,.]+', text)
                                if price_match:
                                    found_price = price_match.group(0)
                                    # Ensure it's not the same as the current price
                                    if clean_price(found_price) != clean_price(result["RSP"]):
                                        html_original_price = found_price
                                        break
                        except: pass
                    
                    if html_original_price:
                        result["Original Price"] = html_original_price
                    # Seller
                    if result["Seller"] == "N/A":
                        # Try multiple selectors for seller
                        seller_selectors = ['.seller-name span', '.seller-name a', '[data-ref="seller-name"]', '.pdp-module_seller-name_3-h0m']
                        for sel in seller_selectors:
                            if page.locator(sel).count() > 0:
                                result["Seller"] = page.locator(sel).first.text_content().strip()
                                break
                        
                        # Fallback text search for "Sold by" if selector fails
                        if result["Seller"] == "N/A":
                            try:
                                # Get all elements containing "Sold by"
                                sold_by_elements = page.get_by_text("Sold by", exact=False).all()
                                for el in sold_by_elements:
                                    raw_text = el.text_content()
                                    # Normalize text (remove newlines, extra spaces)
                                    text = " ".join(raw_text.split())
                                    
                                    if "Sold by" in text:
                                        # Extract part after "Sold by"
                                        after_sold_by = text.split("Sold by")[-1].strip()
                                        
                                        # Cleanup: Remove "Fulfilled by..." and other common suffixes
                                        candidate = after_sold_by.split("Fulfilled")[0].strip()
                                        candidate = candidate.split("Seller Score")[0].strip() # Handle user example case
                                        
                                        # Heuristic: A valid seller name is usually short (e.g., < 50 chars)
                                        # and shouldn't just be "Takealot" if we are looking for 3rd parties (though it could be).
                                        if 0 < len(candidate) < 50:
                                            result["Seller"] = candidate
                                            break
                            except: pass
                        
                        # Check for "Sold by Takealot" explicitly if still N/A
                        if result["Seller"] == "N/A":
                            body_text_lower = page.inner_text('body').lower()
                            if "sold by takealot" in body_text_lower:
                                result["Seller"] = "Takealot"

                        # Default to Takealot if still N/A (User request)
                        if result["Seller"] == "N/A":
                            result["Seller"] = "Takealot"

                    # Province / Location Availability
                    if result["Province"] == "N/A":
                        found_locs = []
                        # Check for specific shipping text patterns
                        if page.get_by_text("shipped from Durban", exact=False).count() > 0:
                            found_locs.append("DBN")
                        if page.get_by_text("shipped from Johannesburg", exact=False).count() > 0:
                            found_locs.append("JHB")
                        if page.get_by_text("shipped from Cape Town", exact=False).count() > 0:
                            found_locs.append("CPT")
                        
                        if found_locs:
                            result["Province"] = ", ".join(found_locs)

                    
                    # Stock
                    if result["Stock Availability"] == "N/A":
                        # Check for specific "Supplier out of stock" text as per user report
                        if page.get_by_text("Supplier out of stock").count() > 0:
                             result["Stock Availability"] = "Supplier out of stock"
                        elif page.locator('.stock-availability').count() > 0:
                            result["Stock Availability"] = page.locator('.stock-availability').first.text_content().strip()
                        elif page.locator('[data-ref="stock-availability"]').count() > 0:
                            result["Stock Availability"] = page.locator('[data-ref="stock-availability"]').first.text_content().strip()
                        
                        # Fallback Logic: Check for negative indicators, otherwise assume In Stock
                        if result["Stock Availability"] == "N/A":
                            body_text_lower = page.inner_text('body').lower()
                            if "out of stock" in body_text_lower or "sold out" in body_text_lower:
                                result["Stock Availability"] = "Out of Stock"
                            else:
                                # If we are here, we found no evidence of it being out of stock
                                result["Stock Availability"] = "In Stock"
                    
                    # Rating & Review Count (HTML Fallback)
                    if result["Rating"] == "N/A" or result["Review Count"] == "N/A":
                         try:
                            # Find all elements containing "Review" (covers "Reviews" and "Review")
                            review_els = page.get_by_text("Review", exact=False).all()
                            for el in review_els:
                                text = el.text_content().strip()
                                
                                count_found = None
                                
                                # Strategy 1: "56 Reviews" in text
                                matches = re.search(r'(\d+)\s*Review', text, re.IGNORECASE)
                                if matches:
                                    count_found = matches.group(1)
                                
                                # Strategy 2: Text is just "Reviews", count is previous sibling
                                elif text.lower() in ["reviews", "review", "(reviews)", "reviews)"]:
                                    try:
                                        prev_text = el.evaluate("el => el.previousElementSibling ? el.previousElementSibling.innerText : ''").strip()
                                        if prev_text.isdigit():
                                            count_found = prev_text
                                    except: pass

                                if count_found:
                                    result["Review Count"] = count_found
                                    
                                    # Try to find Rating near this element
                                    # Context Strategy: Previous Sibling
                                    try:
                                        prev = el.evaluate("el => el.previousElementSibling ? el.previousElementSibling.innerText : ''")
                                        # If prev was the count, check prev-prev for rating
                                        if prev.strip() == count_found:
                                             prev = el.evaluate("el => el.previousElementSibling && el.previousElementSibling.previousElementSibling ? el.previousElementSibling.previousElementSibling.innerText : ''")
                                        
                                        if prev and re.match(r'^\d\.\d$', prev.strip()):
                                            result["Rating"] = prev.strip()
                                    except: pass
                                    
                                    # Context Strategy: Parent's text
                                    if result["Rating"] == "N/A":
                                        try:
                                            parent_text = el.evaluate("el => el.parentElement ? el.parentElement.innerText : ''")
                                            rating_match = re.search(r'(\d\.\d)', parent_text)
                                            if rating_match:
                                                result["Rating"] = rating_match.group(1)
                                        except: pass
                                    
                                    break # Found a count, stop
                            
                            # Fallback for Rating if still N/A
                            if result["Rating"] == "N/A":
                                 # Look for the big number rating usually at top
                                 rating_el = page.locator('.rating-score').first
                                 if rating_el.count() > 0:
                                     result["Rating"] = rating_el.text_content().strip()
                                 else:
                                     # Try searching for text that looks like a rating "4.2" standing alone
                                     potential_ratings = page.get_by_text(re.compile(r'^\s*\d\.\d\s*$')).all()
                                     for pr in potential_ratings:
                                         try:
                                             val = float(pr.text_content().strip())
                                             if 1.0 <= val <= 5.0:
                                                 result["Rating"] = str(val)
                                                 break
                                         except: pass

                         except Exception as e:
                             print(f"Error in HTML fallback for reviews: {e}")

                # --- Final Cleanup ---
                result["RSP"] = clean_price(result["RSP"])
                result["Original Price"] = clean_price(result["Original Price"])
                
                if result["RSP"] == "N/A" or result["RSP"] == "":
                    # Fallback text search
                    body_text = page.inner_text("body")
                    extracted = extract_price_from_text(body_text)
                    if extracted:
                        result["RSP"] = extracted
                    else:
                        result["Error"] = "Price Not Found"
                
                results.append(result)
                print(f"  > Scraped: {result['Description'][:30]}... | Price: {result['RSP']}")
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                result["Error"] = str(e)[:100]
                results.append(result)
        
        browser.close()
    
    return results

def scrape_product(url):
    """Wrapper for backward compatibility"""
    results = scrape_products_batch([url])
    return results[0]