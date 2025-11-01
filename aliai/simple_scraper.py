"""
Simple AliExpress Product Scraper
Just passes in a URL and logs the scraped data

Usage:
    python simple_scraper.py
    
    Or modify the test_url in main() to scrape a different product.

This scraper uses Selenium with undetected Chrome to handle JavaScript-rendered content
and extracts product information including title, price, images, and more.
"""

from bs4 import BeautifulSoup
from loguru import logger
import undetected_chromedriver as uc
import time
from selenium.webdriver.common.by import By

# Configure logger to be more readable
logger.remove()
logger.add(lambda msg: print(msg), format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


def scrape_aliexpress_product(url: str):
    """Scrape an AliExpress product page and log the data using Selenium"""
    logger.info(f"Starting scrape for: {url}")
    
    # Setup undetected Chrome
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        logger.info("Initializing Chrome driver...")
        driver = uc.Chrome(options=options, version_main=141)
        
        logger.info("Navigating to URL...")
        driver.get(url)
        
        # Wait for page to load
        logger.info("Waiting for page to load...")
        time.sleep(5)  # Give JavaScript time to render
        
        # Get the rendered HTML
        html = driver.page_source
        logger.success(f"Successfully fetched page ({len(html)} bytes)")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract product information
        logger.info("\n" + "="*60)
        logger.info("EXTRACTED PRODUCT DATA")
        logger.info("="*60)
        
        # First, try OpenGraph meta tags (most reliable)
        og_title = soup.find('meta', property='og:title')
        if og_title:
            logger.info(f"Title (OG): {og_title.get('content', 'N/A')}")
        
        og_image = soup.find('meta', property='og:image')
        if og_image:
            logger.info(f"Main Image (OG): {og_image.get('content', 'N/A')}")
        
        # Extract product ID from URL
        import re as regex_module
        product_id_match = regex_module.search(r'/item/(\d+)', url)
        if product_id_match:
            logger.info(f"Product ID: {product_id_match.group(1)}")
        
        # Look for JSON data in the page
        logger.info("\nSearching for JSON data in page...")
        json_pattern = regex_module.compile(r'window\.runParams\s*=\s*({.+?});', regex_module.DOTALL)
        matches = json_pattern.findall(html)
        if matches:
            logger.info(f"Found {len(matches)} potential JSON data blocks")
            try:
                import json
                json_data = json.loads(matches[0])
                logger.info("\nParsed JSON data structure keys:")
                if isinstance(json_data, dict):
                    logger.info(list(json_data.keys())[:20])
                else:
                    logger.info(f"Type: {type(json_data)}")
            except Exception as e:
                logger.warning(f"Could not parse JSON: {e}")
        
        # Try to extract visible page elements using Selenium
        logger.info("\n--- Attempting to find visible elements ---")
        
        try:
            # Try to get product title
            title_selectors = [
                'h1[data-pl="product-title"]',
                'h1.product-title-text',
                'h1',
                '[class*="product-title"]'
            ]
            for selector in title_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if text and text not in ['Aliexpress', 'AliExpress', '']:
                        logger.info(f"Title (HTML): {text}")
                        break
                except:
                    continue
            
            # Try to get price - look for current price specifically
            try:
                current_price = driver.find_element(By.CSS_SELECTOR, 'span[data-pl="product-current-price"]')
                logger.info(f"Current Price: {current_price.text.strip()}")
            except:
                # Fallback to other price selectors
                price_selectors = [
                    '.product-price-value',
                    '.notranslate',
                    '[class*="price"]'
                ]
                for selector in price_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            text = elem.text.strip()
                            if text and any(c in text for c in ['$', '€', '£', '¥', 'USD']) and len(text) < 50:
                                # Skip if it's a discount text or other non-price info
                                if 'save' in text.lower() or 'ends' in text.lower():
                                    continue
                                logger.info(f"Price: {text}")
                                raise StopIteration  # Exit both loops
                    except StopIteration:
                        break
                    except:
                        continue
            
            # Try to get original price if discounted
            try:
                original_price = driver.find_element(By.CSS_SELECTOR, 'span[data-pl="product-original-price"]')
                logger.info(f"Original Price: {original_price.text.strip()}")
            except:
                pass
            
            # Try to get seller/store info
            try:
                seller = driver.find_element(By.CSS_SELECTOR, 'a[data-pl="store-info-name"]')
                logger.info(f"Seller: {seller.text.strip()}")
            except:
                pass
            
            # Try to get images
            try:
                images = driver.find_elements(By.CSS_SELECTOR, 'img[class*="product"], img[class*="gallery"]')
                if images:
                    logger.info(f"\nFound {len(images)} potential product images")
                    for i, img in enumerate(images[:10], 1):
                        src = img.get_attribute('src') or img.get_attribute('data-src')
                        if src and 'alicdn.com' in src:
                            logger.info(f"  Image {i}: {src[:120]}...")
            except:
                pass
            
            # Try to get reviews count
            try:
                review_count = driver.find_element(By.CSS_SELECTOR, '[data-pl="review-count"]')
                logger.info(f"Review Count: {review_count.text.strip()}")
            except:
                pass
            
            # Try to get rating
            try:
                rating = driver.find_element(By.CSS_SELECTOR, '[data-pl="product-rating"]')
                logger.info(f"Rating: {rating.text.strip()}")
            except:
                pass
                
            # Try to get sales count
            try:
                sales = driver.find_element(By.CSS_SELECTOR, '[data-pl="product-sales"]')
                logger.info(f"Sales: {sales.text.strip()}")
            except:
                pass
                
        except Exception as e:
            logger.warning(f"Error extracting visible elements: {e}")
        
        logger.info("="*60)
        logger.info("END OF EXTRACTED DATA")
        logger.info("="*60)
        
        # Close the driver
        driver.quit()
        logger.info("Chrome driver closed")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise


def main():
    """Main entry point"""
    # The example URL from the user
    test_url = "https://www.aliexpress.us/item/3256810016116999.html"
    
    logger.info("Simple AliExpress Product Scraper")
    logger.info(f"Target URL: {test_url}\n")
    
    scrape_aliexpress_product(test_url)


if __name__ == "__main__":
    main()

