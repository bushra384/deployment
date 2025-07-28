from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import threading
import re
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)  # This allows every domain

# Global variables for driver management
driver = None
driver_lock = threading.Lock()
is_scraping = False

def get_driver():
    global driver
    if driver is None:
        options = Options()
        # options.add_argument("--headless")  # Optional
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("start-maximized")
        options.add_argument("user-agent=Mozilla/5.0")
        driver = webdriver.Chrome(options=options)
    return driver

def close_driver():
    global driver
    if driver:
        try:
            driver.quit()
        except:
            pass
        driver = None

def scrape_noon_products():
    global is_scraping
    
    with driver_lock:
        if is_scraping:
            return {"error": "Scraping already in progress. Please wait."}
        
        is_scraping = True
    
    try:
        driver = get_driver()
        all_products = []

        url = "https://minutes.noon.com/uae-en/search/?f[category]=fruits_vegetables"
        print(f"\n🔍 Scraping all fruits and vegetables")
        driver.get(url)

        wait = WebDriverWait(driver, 15)
        page = 1
        
        while True:
            print(f"\n🔍 Scraping page {page}")
            
            try:
                wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.catalogList_instantCatalogWrapper__s2Fyy"
                )))
            except:
                print(f"⚠️ No product grid found on page {page}. Stopping...")
                break

            # Try multiple selectors to find product cards
            product_cards = driver.find_elements(By.CSS_SELECTOR,
                "div.catalogList_instantCatalogList__gUTOP a > div > div > div.css-g5y9jx")
            
            # If no products found with first selector, try alternative
            if not product_cards:
                product_cards = driver.find_elements(By.CSS_SELECTOR,
                    "div.catalogList_instantCatalogList__gUTOP a")
                print(f"Trying alternative selector, found {len(product_cards)} cards")

            print(f"🛒 Found {len(product_cards)} products on page {page}")
            
            # If no products found, we've reached the end
            if not product_cards:
                print(f"⚠️ No products found on page {page}. Stopping...")
                break

            page_products = 0
            for card in product_cards:
                try:
                    data = card.text.strip().split("\n")
                    print(f"Card data: {data[:3]}...")  # Debug: show first 3 elements
                    
                    # Extract product ID from parent <a> href
                    product_id = None
                    try:
                        parent_a = card.find_element(By.XPATH, "./ancestor::a[1]")
                        href = parent_a.get_attribute("href")
                        if href and '/now-product/' in href:
                            # Extract the ID between /now-product/ and the next /
                            match = re.search(r'/now-product/([^/]+)/', href)
                            if match:
                                product_id = match.group(1)
                    except Exception as e:
                        print(f"Could not extract product_id: {e}")
                        pass

                    # Filter out promotional and non-product elements
                    filtered_data = []
                    for item in data:
                        item = item.strip()
                        # Skip promotional elements
                        if (item.upper() in ['ADD', 'OFF', 'ON', 'SALE', 'NEW', 'HOT'] or
                            '%' in item or  # Skip percentage discounts
                            item.isdigit() and len(item) <= 2 or  # Skip small numbers (like "14")
                            item.startswith('AED') or  # Skip standalone AED
                            len(item) <= 2 and item.isalpha()):  # Skip very short text
                            continue
                        filtered_data.append(item)
                    
                    # If we don't have enough meaningful data after filtering, skip
                    if len(filtered_data) < 3:
                        print(f"Skipping promotional element: {data}")
                        continue

                    # Remove "ADD" button or unexpected lines from filtered data
                    if filtered_data[0].strip().upper() == "ADD":
                        filtered_data.pop(0)

                    # Extract product image URL - look for product images specifically
                    image_url = ""
                    try:
                        # Strategy 1: Look in current card
                        img_elements = card.find_elements(By.CSS_SELECTOR, "img")
                        for img in img_elements:
                            src = img.get_attribute("src")
                            if src and "f.nooncdn.com/" in src:
                                image_url = src
                                break
                        
                        # Strategy 2: If no image found, look in parent elements
                        if not image_url:
                            try:
                                parent_link = card.find_element(By.XPATH, "./ancestor::a")
                                img_elements = parent_link.find_elements(By.CSS_SELECTOR, "img")
                                for img in img_elements:
                                    src = img.get_attribute("src")
                                    if src and "f.nooncdn.com/" in src:
                                        image_url = src
                                        break
                            except:
                                pass
                        
                        # Strategy 3: Look in sibling elements
                        if not image_url:
                            try:
                                parent = card.find_element(By.XPATH, "./..")
                                img_elements = parent.find_elements(By.CSS_SELECTOR, "img")
                                for img in img_elements:
                                    src = img.get_attribute("src")
                                    if src and "f.nooncdn.com/" in src:
                                        image_url = src
                                        break
                            except:
                                pass
                        
                        # Strategy 4: Look in the entire product container
                        if not image_url:
                            try:
                                product_container = card.find_element(By.XPATH, "./ancestor::div[contains(@class, 'catalogList')]")
                                img_elements = product_container.find_elements(By.CSS_SELECTOR, "img")
                                for img in img_elements:
                                    src = img.get_attribute("src")
                                    if src and "f.nooncdn.com/" in src and "cms" not in src:
                                        image_url = src
                                        break
                            except:
                                pass
                                
                    except Exception as e:
                        pass

                    # Create product with more flexible data handling
                    product = {
                        "product_id": product_id,
                        "origin": filtered_data[0] if len(filtered_data) > 0 else "",
                        "name": filtered_data[1] if len(filtered_data) > 1 else "",
                        "size": filtered_data[2] if len(filtered_data) > 2 else "",
                        "price": "",
                        "original_price": "",
                        "image_url": image_url,
                        "page": page
                    }

                    # Handle pricing - look for any numeric values
                    prices = []
                    for d in filtered_data:
                        if "AED" in d or "\uef01" in d:
                            prices.append(d)
                        elif d.replace(".", "").replace(",", "").isdigit():
                            prices.append(d)

                    prices = [p.replace("\uef01", "").replace("AED", "").strip() for p in prices if p.strip()]

                    if len(prices) == 1:
                        product["price"] = prices[0]
                    elif len(prices) >= 2:
                        product["price"] = prices[0]
                        product["original_price"] = prices[1]

                    all_products.append(product)
                    page_products += 1
                    print(f"✅ Added product: {product['name']}")

                except Exception as e:
                    print(f"⚠️ Error parsing product card: {e}")
                    continue

            print(f"📊 Page {page}: Added {page_products} products (Total: {len(all_products)})")

            # Try to click the next button (">" arrow)
            try:
                # Find the next page <a> element
                next_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "a[role='button'][aria-label='Next page'][rel='next'][aria-disabled='false']"
                )
                next_href = next_btn.get_attribute("href")
                if next_href:
                    # Make sure the href is an absolute URL
                    next_url = urljoin(driver.current_url, next_href)
                    print(f"Navigating to next page: {next_url}")
                    driver.get(next_url)
                    time.sleep(4)  # Wait for the next page to load
                    page += 1 # Increment page number
                else:
                    print("No next href found or next button is disabled. Stopping.")
                    break
            except Exception as e:
                print(f"No next <a> button found or error navigating: {e}")
                break

        print(f"✅ Successfully scraped {len(all_products)} products from {page} pages")
        return all_products

    except Exception as e:
        print(f"Error during scraping: {e}")
        return []
    finally:
        is_scraping = False

@app.route("/search", methods=["GET"])
def search():
    result = scrape_noon_products()
    # Count unique pages
    unique_pages = set()
    for product in result:
        if 'page' in product and product['page']:
            unique_pages.add(product['page'])
    if len(unique_pages) >= 5:
        # Save to JSON file
        with open("noon_products.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        return jsonify(result)
    else:
        # Return existing JSON file data
        try:
            with open("noon_products.json", "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            return jsonify(existing_data)
        except Exception as e:
            return jsonify({"error": "Not enough data scraped and no previous data found.", "details": str(e)}), 500

@app.route("/download", methods=["GET"])
def download():
    # Return the JSON file as a download
    return send_file("noon_products.json", as_attachment=True, mimetype="application/json")

@app.route("/", methods=["GET"])
def status():
    return jsonify({"is_scraping": is_scraping})

@app.route("/product-details/<product_id>", methods=["GET"])
def product_details(product_id):
    image_url_fallback = request.args.get("image_url")
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("start-maximized")
    options.add_argument("user-agent=Mozilla/5.0")
    print(f"Scraping product details for {product_id}")
    driver = webdriver.Chrome(options=options)
    try:
        url = f"https://minutes.noon.com/uae-en/now-product/{product_id}/"
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        try:
            wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "h1"
            )))
        except:
            print(driver.page_source[:1500])
            driver.quit()
            return jsonify({"error": "Product details not found (h1 not loaded)"}), 404
        # Name
        try:
            name = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
        except:
            name = None
        # Weight/Size
        try:
            size = driver.find_element(By.CSS_SELECTOR, "div[class*='ProductDetails_infoWrapper'] > div").text.strip()
        except:
            size = None
        # Image
        try:
            imgs = driver.find_elements(By.TAG_NAME, "img")
            image_url = None
            for img in imgs:
                src = img.get_attribute("src")
                if src and "/p/pzsku/" in src:
                    image_url = src
                    break
            if not image_url:
                image_url = image_url_fallback
        except:
            image_url = image_url_fallback
        # Description and features
        desc = None
        features = []
        try:
            # Try the styled div first
            desc_divs = driver.find_elements(By.CSS_SELECTOR, "div[style*='margin-top: 20px'][style*='color: rgb(126, 133, 155)']")
            for div in desc_divs:
                # If it has a <p>, use that
                try:
                    desc = div.find_element(By.TAG_NAME, "p").text.strip()
                except:
                    # Otherwise, use the div's text
                    desc = div.text.strip()
                try:
                    features = [li.text.strip() for li in div.find_elements(By.TAG_NAME, "li")]
                except:
                    features = []
                if desc:
                    break
        except:
            desc = None
            features = []
        # If still not found, try all <div> as fallback
        if not desc:
            try:
                divs = driver.find_elements(By.TAG_NAME, "div")
                for div in divs:
                    t = div.text.strip()
                    if t and len(t) > 30 and 'fruit' in t.lower():  # crude filter for a real description
                        desc = t
                        break
            except:
                pass
        if not desc:
            print("--- PAGE SOURCE FOR DEBUGGING ---")
            print(driver.page_source[:2000])
            print("--- END PAGE SOURCE ---")
        # Price and original price
        price = None
        original_price = None
        try:
            price_els = driver.find_elements(By.XPATH, "//span[contains(text(), 'AED') or contains(text(), 'د.إ') or contains(text(), '.')]")
            price_candidates = [el.text.strip() for el in price_els if el.text.strip() and any(c.isdigit() for c in el.text)]
            if len(price_candidates) > 0:
                price = price_candidates[0]
            if len(price_candidates) > 1:
                original_price = price_candidates[1]
        except:
            pass
        # Delivery
        delivery = None
        try:
            delivery_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'Arrives in')]")
            if delivery_els:
                delivery = delivery_els[0].text.strip()
        except:
            pass
        driver.quit()
        return jsonify({
            "product_id": product_id,
            "name": name,
            "size": size,
            "price": price,
            "original_price": original_price,
            "delivery": delivery,
            "description": desc,
            "features": features,
            "image_url": image_url
        })
    except Exception as e:
        driver.quit()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    try:
        app.run(debug=True)
    finally:
        close_driver()
