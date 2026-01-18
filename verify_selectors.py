from playwright.sync_api import sync_playwright
import re

def clean_price(price_str):
    if not price_str:
        return "N/A"
    clean = re.sub(r'[^\d.,]', '', str(price_str))
    return clean.strip()

def test_takealot_extraction(page):
    print("Testing Takealot Extraction...")
    # Mock HTML based on user input
    # "R 1,799 and then the orignal price is just after this here: <span class=\"currency plus currency-module_currency_29IIm\">R 2,199</span>"
    # I will assume a container.
    html = """
    <html>
    <body>
        <div class=\"pdp-main-panel\">
            <div class=\"buy-box\">
                <div class=\"price-container\">
                    <span class=\"currency plus currency-module_currency_29IIm\">R 1,799</span>
                    <span class=\"currency plus currency-module_currency_29IIm\">R 2,199</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    page.set_content(html)
    
    # Current Logic Simulation (Simplified)
    # The current logic looks for specific classes like .buy-box-price or next_data
    # We want to test the NEW logic we want to add.
    
    result = {"RSP": "N/A", "Original Price": "N/A"}
    
    product_container = page.locator('.pdp-main-panel').first
    
    # Proposed New Logic
    currency_elements = product_container.locator('span[class*="currency"][class*="plus"]').all()
    print(f"Found {len(currency_elements)} currency elements")
    
    prices = []
    for el in currency_elements:
        txt = el.text_content().strip()
        if 'R' in txt:
            prices.append(txt)
            
    if len(prices) >= 2:
        result["RSP"] = prices[0]
        result["Original Price"] = prices[1]
    elif len(prices) == 1:
        result["RSP"] = prices[0]
        
    print(f"Result: {result}")
    assert result["RSP"] == "R 1,799"
    assert result["Original Price"] == "R 2,199"

def test_amazon_extraction(page):
    print("\nTesting Amazon Extraction...")
    # Mock HTML based on user input
    # "R 5 689,00 with 24 percent savings-24% R5 689,00"
    # "List Price: R 7 499,00"
    html = """
    <html>
    <body>
        <div id="ppd">
            <span id="productTitle">Belkin Thunderbolt 4 Dock Pro</span>
            <div id="corePriceDisplay_desktop_feature_div">
                <div class="a-section a-spacing-none aok-align-center">
                    <span class="a-price aok-align-center reinventPricePriceToPayMargin priceToPay">
                        <span class="a-offscreen">R5 689,00</span>
                        <span aria-hidden="true">
                            <span class="a-price-symbol">R</span>
                            <span class="a-price-whole">5 689<span class="a-price-decimal">,</span></span>
                            <span class="a-price-fraction">00</span>
                        </span>
                    </span>
                    <span id="savingsPercentage" class="a-size-large a-color-price savingPriceOverride aok-align-center reinventPriceSavingsPercentageMargin">
                        -24%
                    </span>
                </div>
                <div class="a-section a-spacing-small aok-align-center">
                    <span class="a-size-small a-color-secondary">List Price: </span>
                    <span class="a-price a-text-price" data-a-strike="true" data-a-color="secondary">
                        <span class="a-offscreen">R7 499,00</span>
                        <span aria-hidden="true">R 7 499,00</span>
                    </span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    page.set_content(html)
    
    result = {"RSP": "N/A", "Original Price": "N/A", "Description": "N/A"}
    
    # Title
    if page.locator('#productTitle').count() > 0:
        result["Description"] = page.locator('#productTitle').first.text_content().strip()
        
    # Proposed New Logic for Amazon
    
    # 1. Price
    # Look for a-price-whole if offscreen fails or as backup
    whole = page.locator('.a-price-whole').first
    fraction = page.locator('.a-price-fraction').first
    if whole.count() > 0:
        w = whole.text_content().strip()
        f = fraction.text_content().strip() if fraction.count() > 0 else "00"
        result["RSP"] = f"R {w}.{f}"

    # 2. Original Price - Look for "List Price:" text
    # Finding the element that contains "List Price:"
    list_price_label = page.get_by_text("List Price:", exact=False).first
    if list_price_label.count() > 0:
        # Check siblings or children of parent
        # Usually it's: <span>List Price:</span> <span class="a-text-price">...</span>
        # So we look at the parent's text or next sibling
        
        # Try Next Sibling first
        # Playwright doesn't have a direct "next_sibling" selector easily, but we can use xpath or layout
        
        # Strategy: Find the price inside the same container
        parent = list_price_label.locator('..')
        price_el = parent.locator('.a-text-price span.a-offscreen').first
        if price_el.count() > 0:
             result["Original Price"] = price_el.text_content().strip()
        else:
            # Maybe it is just text in the parent
            text = parent.inner_text()
            # Extract R ...
            # "List Price: R 7 499,00"
            matches = re.findall(r'List Price:\s*(R\s?[\d,.\s]+)', text, re.IGNORECASE)
            if matches:
                result["Original Price"] = matches[0].strip()

    print(f"Result: {result}")
    
    # Normalize for check
    rsp_clean = clean_price(result["RSP"])
    op_clean = clean_price(result["Original Price"])
    
    assert "5689" in rsp_clean # 5 689,00 -> 5689,00
    assert "7499" in op_clean

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    test_takealot_extraction(page)
    test_amazon_extraction(page)
    browser.close()
    print("All tests passed!")
