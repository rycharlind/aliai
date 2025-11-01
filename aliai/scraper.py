"""
AliAI - Core Scraper Module
Handles web scraping with rate limiting, proxy support, and retry logic
"""

import asyncio
import random
import time
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import aiohttp
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger
from .config import get_config


@dataclass
class ScrapingResult:
    """Result of a scraping operation"""
    url: str
    status_code: int
    content: str
    headers: Dict[str, str]
    response_time: float
    proxy_used: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ProductData:
    """Structured product data from AliExpress"""
    product_id: str
    title: str
    price: float
    original_price: Optional[float]
    discount_percentage: Optional[int]
    currency: str
    shipping_cost: Optional[float]
    free_shipping: bool
    seller_id: str
    seller_name: str
    seller_rating: Optional[float]
    category_id: str
    category_name: str
    brand: Optional[str]
    product_url: str
    image_urls: List[str]
    tags: List[str]
    total_reviews: int
    average_rating: Optional[float]
    total_sales: int
    stock_quantity: Optional[int]
    is_available: bool
    scraped_at: str


class RateLimiter:
    """Rate limiter for respectful scraping"""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_requests = []
        self.hour_requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request"""
        async with self.lock:
            now = time.time()
            
            # Clean old requests
            self.minute_requests = [req_time for req_time in self.minute_requests 
                                  if now - req_time < 60]
            self.hour_requests = [req_time for req_time in self.hour_requests 
                                if now - req_time < 3600]
            
            # Check limits
            if len(self.minute_requests) >= self.requests_per_minute:
                sleep_time = 60 - (now - self.minute_requests[0])
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.acquire()
            
            if len(self.hour_requests) >= self.requests_per_hour:
                sleep_time = 3600 - (now - self.hour_requests[0])
                logger.info(f"Hourly rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                return await self.acquire()
            
            # Record this request
            self.minute_requests.append(now)
            self.hour_requests.append(now)


class ProxyManager:
    """Manages proxy rotation and health checking"""
    
    def __init__(self, proxy_list: List[str], rotation: bool = True):
        self.proxy_list = proxy_list
        self.rotation = rotation
        self.current_index = 0
        self.failed_proxies = set()
        self.ua = UserAgent()
    
    def get_proxy(self) -> Optional[str]:
        """Get next available proxy"""
        if not self.proxy_list:
            return None
        
        available_proxies = [p for p in self.proxy_list if p not in self.failed_proxies]
        if not available_proxies:
            # Reset failed proxies if all are marked as failed
            self.failed_proxies.clear()
            available_proxies = self.proxy_list
        
        if self.rotation:
            proxy = available_proxies[self.current_index % len(available_proxies)]
            self.current_index += 1
        else:
            proxy = random.choice(available_proxies)
        
        return proxy
    
    def mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed"""
        self.failed_proxies.add(proxy)
        logger.warning(f"Marked proxy {proxy} as failed")
    
    def get_user_agent(self) -> str:
        """Get a random user agent"""
        return self.ua.random


class AliExpressScraper:
    """Main scraper class for AliExpress"""
    
    def __init__(self):
        self.config = get_config()
        self.rate_limiter = RateLimiter(
            self.config.scraping.rate_limit_per_minute,
            self.config.scraping.rate_limit_per_hour
        )
        self.proxy_manager = ProxyManager(
            self.config.proxy.proxy_list_parsed,
            self.config.proxy.rotation
        )
        self.session = None
        self.base_url = "https://www.aliexpress.com"
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=self.config.scraping.max_concurrent_requests)
        timeout = aiohttp.ClientTimeout(total=self.config.scraping.timeout)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, url: str, retries: int = None) -> ScrapingResult:
        """Make a single HTTP request with retry logic"""
        if retries is None:
            retries = self.config.scraping.max_retries
        
        await self.rate_limiter.acquire()
        
        proxy = self.proxy_manager.get_proxy() if self.config.proxy.enabled else None
        user_agent = self.proxy_manager.get_user_agent()
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        proxy_url = f"http://{proxy}" if proxy else None
        
        start_time = time.time()
        
        for attempt in range(retries + 1):
            try:
                async with self.session.get(
                    url, 
                    headers=headers, 
                    proxy=proxy_url,
                    ssl=False
                ) as response:
                    content = await response.text()
                    response_time = time.time() - start_time
                    
                    return ScrapingResult(
                        url=url,
                        status_code=response.status,
                        content=content,
                        headers=dict(response.headers),
                        response_time=response_time,
                        proxy_used=proxy
                    )
                    
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retries + 1}): {e}")
                
                if proxy:
                    self.proxy_manager.mark_proxy_failed(proxy)
                
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return ScrapingResult(
                        url=url,
                        status_code=0,
                        content="",
                        headers={},
                        response_time=time.time() - start_time,
                        proxy_used=proxy,
                        error=str(e)
                    )
    
    def _parse_product_page(self, html: str, url: str) -> Optional[ProductData]:
        """Parse product data from HTML content"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract product ID from URL
            product_id = self._extract_product_id(url)
            
            # Extract title
            title_element = soup.find('h1', {'class': 'product-title-text'})
            title = title_element.get_text(strip=True) if title_element else "Unknown Product"
            
            # Extract price information
            price_element = soup.find('span', {'class': 'notranslate'})
            price = self._parse_price(price_element.get_text() if price_element else "0")
            
            # Extract seller information
            seller_element = soup.find('a', {'class': 'store-name'})
            seller_name = seller_element.get_text(strip=True) if seller_element else "Unknown Seller"
            seller_id = self._extract_seller_id(seller_element.get('href', '')) if seller_element else "unknown"
            
            # Extract category information
            category_element = soup.find('a', {'class': 'breadcrumb-item'})
            category_name = category_element.get_text(strip=True) if category_element else "Unknown Category"
            category_id = self._extract_category_id(category_element.get('href', '')) if category_element else "unknown"
            
            # Extract image URLs
            image_elements = soup.find_all('img', {'class': 'product-image'})
            image_urls = [img.get('src', '') for img in image_elements if img.get('src')]
            
            # Extract review information
            review_element = soup.find('span', {'class': 'review-count'})
            total_reviews = self._parse_number(review_element.get_text() if review_element else "0")
            
            # Extract rating
            rating_element = soup.find('span', {'class': 'rating-value'})
            average_rating = self._parse_rating(rating_element.get_text() if rating_element else "0")
            
            return ProductData(
                product_id=product_id,
                title=title,
                price=price,
                original_price=None,  # Would need additional parsing
                discount_percentage=None,
                currency="USD",
                shipping_cost=None,
                free_shipping=False,
                seller_id=seller_id,
                seller_name=seller_name,
                seller_rating=None,
                category_id=category_id,
                category_name=category_name,
                brand=None,
                product_url=url,
                image_urls=image_urls,
                tags=[],
                total_reviews=total_reviews,
                average_rating=average_rating,
                total_sales=0,
                stock_quantity=None,
                is_available=True,
                scraped_at=time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
        except Exception as e:
            logger.error(f"Error parsing product page {url}: {e}")
            return None
    
    def _extract_product_id(self, url: str) -> str:
        """Extract product ID from URL"""
        # AliExpress URLs typically contain product IDs
        # This is a simplified extraction - would need more robust parsing
        parts = url.split('/')
        for part in parts:
            if part.startswith('item/') or part.startswith('product/'):
                return part.split('/')[-1].split('.')[0]
        return "unknown"
    
    def _extract_seller_id(self, seller_url: str) -> str:
        """Extract seller ID from seller URL"""
        if not seller_url:
            return "unknown"
        parts = seller_url.split('/')
        for part in parts:
            if part.startswith('store/') or part.startswith('seller/'):
                return part.split('/')[-1]
        return "unknown"
    
    def _extract_category_id(self, category_url: str) -> str:
        """Extract category ID from category URL"""
        if not category_url:
            return "unknown"
        parts = category_url.split('/')
        for part in parts:
            if part.startswith('category/') or part.startswith('cat/'):
                return part.split('/')[-1]
        return "unknown"
    
    def _parse_price(self, price_text: str) -> float:
        """Parse price from text"""
        try:
            # Remove currency symbols and commas
            cleaned = ''.join(c for c in price_text if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    
    def _parse_number(self, text: str) -> int:
        """Parse number from text (handles K, M suffixes)"""
        try:
            text = text.lower().replace(',', '')
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            else:
                return int(text)
        except ValueError:
            return 0
    
    def _parse_rating(self, rating_text: str) -> Optional[float]:
        """Parse rating from text"""
        try:
            return float(rating_text)
        except ValueError:
            return None
    
    async def scrape_product(self, product_url: str) -> Optional[ProductData]:
        """Scrape a single product page"""
        logger.info(f"Scraping product: {product_url}")
        
        result = await self._make_request(product_url)
        
        if result.error or result.status_code != 200:
            logger.error(f"Failed to scrape {product_url}: {result.error}")
            return None
        
        return self._parse_product_page(result.content, product_url)
    
    async def scrape_category(self, category_url: str, max_pages: int = 10) -> List[ProductData]:
        """Scrape products from a category page"""
        logger.info(f"Scraping category: {category_url} (max {max_pages} pages)")
        
        products = []
        
        for page in range(1, max_pages + 1):
            page_url = f"{category_url}?page={page}"
            result = await self._make_request(page_url)
            
            if result.error or result.status_code != 200:
                logger.error(f"Failed to scrape category page {page}: {result.error}")
                continue
            
            # Parse product links from the page
            soup = BeautifulSoup(result.content, 'html.parser')
            product_links = soup.find_all('a', {'class': 'product-item'})
            
            if not product_links:
                logger.info(f"No more products found on page {page}")
                break
            
            # Scrape each product
            for link in product_links:
                product_url = urljoin(self.base_url, link.get('href', ''))
                if product_url:
                    product = await self.scrape_product(product_url)
                    if product:
                        products.append(product)
            
            # Add delay between pages
            await asyncio.sleep(self.config.scraping.request_delay)
        
        logger.info(f"Scraped {len(products)} products from category")
        return products
    
    async def scrape_search_results(self, search_query: str, max_pages: int = 5) -> List[ProductData]:
        """Scrape products from search results"""
        search_url = f"{self.base_url}/wholesale?SearchText={search_query}"
        return await self.scrape_category(search_url, max_pages)


# Example usage
async def main():
    """Example usage of the scraper"""
    async with AliExpressScraper() as scraper:
        # Scrape a specific product
        product = await scraper.scrape_product("https://www.aliexpress.com/item/3256810016116999.html")
        if product:
            print(f"Scraped product: {product.title}")
        
        # Scrape search results
        products = await scraper.scrape_search_results("wireless headphones", max_pages=2)
        print(f"Found {len(products)} products")


if __name__ == "__main__":
    asyncio.run(main())
