"""
AliAI - Database Module
Handles ClickHouse database operations and data management
"""

import asyncio
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
from clickhouse_driver import Client
from sqlalchemy import create_engine, text
from loguru import logger
from aliai.config import get_config
from aliai.scraper import ProductData


class ClickHouseClient:
    """ClickHouse database client"""
    
    def __init__(self):
        self.config = get_config()
        self.client = None
        self.engine = None
        self._connect()
    
    def _connect(self):
        """Establish connection to ClickHouse"""
        try:
            # Native ClickHouse client
            self.client = Client(
                host=self.config.database.host,
                port=self.config.database.port,
                user=self.config.database.user,
                password=self.config.database.password,
                database=self.config.database.database
            )
            
            logger.info("Connected to ClickHouse database")
            
            # SQLAlchemy engine for pandas integration (optional)
            # Only create if clickhouse-sqlalchemy is available
            try:
                connection_string = (
                    f"clickhouse://{self.config.database.user}:{self.config.database.password}"
                    f"@{self.config.database.host}:{self.config.database.port}"
                    f"/{self.config.database.database}"
                )
                self.engine = create_engine(connection_string)
                logger.debug("SQLAlchemy engine created for pandas integration")
            except Exception as sqlalchemy_error:
                # SQLAlchemy engine is optional - only needed for pandas integration
                logger.warning(
                    f"Could not create SQLAlchemy engine (optional): {sqlalchemy_error}. "
                    f"Install 'clickhouse-sqlalchemy' for pandas integration. "
                    f"Core database operations will still work."
                )
                self.engine = None
            
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            result = self.client.execute("SELECT 1")
            return result[0][0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def insert_product(self, product: ProductData) -> bool:
        """Insert a single product into the database"""
        try:
            query = """
            INSERT INTO products (
                product_id, title, price, original_price, discount_percentage,
                currency, shipping_cost, free_shipping, seller_id, seller_name,
                seller_rating, seller_followers, category_id, category_name,
                subcategory_id, subcategory_name, brand, sku, product_url,
                image_urls, tags, specifications, total_reviews, average_rating,
                total_sales, stock_quantity, is_available, created_at, updated_at,
                scraped_at, seasonal_tags, trend_score, margin_potential
            ) VALUES (
                %(product_id)s, %(title)s, %(price)s, %(original_price)s, %(discount_percentage)s,
                %(currency)s, %(shipping_cost)s, %(free_shipping)s, %(seller_id)s, %(seller_name)s,
                %(seller_rating)s, %(seller_followers)s, %(category_id)s, %(category_name)s,
                %(subcategory_id)s, %(subcategory_name)s, %(brand)s, %(sku)s, %(product_url)s,
                %(image_urls)s, %(tags)s, %(specifications)s, %(total_reviews)s, %(average_rating)s,
                %(total_sales)s, %(stock_quantity)s, %(is_available)s, %(created_at)s, %(updated_at)s,
                %(scraped_at)s, %(seasonal_tags)s, %(trend_score)s, %(margin_potential)s
            )
            """
            
            data = {
                'product_id': product.product_id,
                'title': product.title,
                'price': product.price,
                'original_price': product.original_price,
                'discount_percentage': product.discount_percentage,
                'currency': product.currency,
                'shipping_cost': product.shipping_cost,
                'free_shipping': product.free_shipping,
                'seller_id': product.seller_id,
                'seller_name': product.seller_name,
                'seller_rating': product.seller_rating,
                'seller_followers': 0,  # Would need additional scraping
                'category_id': product.category_id,
                'category_name': product.category_name,
                'subcategory_id': product.subcategory_id,
                'subcategory_name': product.subcategory_name,
                'brand': product.brand,
                'sku': product.sku,
                'product_url': product.product_url,
                'image_urls': product.image_urls,
                'tags': product.tags,
                'specifications': {},  # Would need additional parsing
                'total_reviews': product.total_reviews,
                'average_rating': product.average_rating,
                'total_sales': product.total_sales,
                'stock_quantity': product.stock_quantity,
                'is_available': product.is_available,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'scraped_at': datetime.strptime(product.scraped_at, '%Y-%m-%d %H:%M:%S'),
                'seasonal_tags': [],
                'trend_score': 0.0,
                'margin_potential': 0.0
            }
            
            self.client.execute(query, data)
            logger.debug(f"Inserted product: {product.product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert product {product.product_id}: {e}")
            return False
    
    async def batch_insert_products(self, products: List[ProductData]) -> int:
        """Insert multiple products in batch"""
        successful_inserts = 0
        
        for product in products:
            if await self.insert_product(product):
                successful_inserts += 1
        
        logger.info(f"Batch inserted {successful_inserts}/{len(products)} products")
        return successful_inserts
    
    async def insert_review(self, review_data: Dict[str, Any]) -> bool:
        """Insert a review into the database"""
        try:
            query = """
            INSERT INTO reviews (
                review_id, product_id, user_id, user_name, user_country,
                rating, review_text, review_date, helpful_votes, verified_purchase,
                sentiment_score, sentiment_label, key_phrases, language,
                translated_text, created_at, scraped_at
            ) VALUES (
                %(review_id)s, %(product_id)s, %(user_id)s, %(user_name)s, %(user_country)s,
                %(rating)s, %(review_text)s, %(review_date)s, %(helpful_votes)s, %(verified_purchase)s,
                %(sentiment_score)s, %(sentiment_label)s, %(key_phrases)s, %(language)s,
                %(translated_text)s, %(created_at)s, %(scraped_at)s
            )
            """
            
            self.client.execute(query, review_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert review: {e}")
            return False
    
    async def insert_price_history(self, product_id: str, price: float, original_price: float = None) -> bool:
        """Insert price history record"""
        try:
            query = """
            INSERT INTO price_history (
                product_id, price, original_price, discount_percentage,
                currency, recorded_at, scraped_at
            ) VALUES (
                %(product_id)s, %(price)s, %(original_price)s, %(discount_percentage)s,
                %(currency)s, %(recorded_at)s, %(scraped_at)s
            )
            """
            
            discount_percentage = 0
            if original_price and original_price > price:
                discount_percentage = int(((original_price - price) / original_price) * 100)
            
            data = {
                'product_id': product_id,
                'price': price,
                'original_price': original_price,
                'discount_percentage': discount_percentage,
                'currency': 'USD',
                'recorded_at': datetime.now(),
                'scraped_at': datetime.now()
            }
            
            self.client.execute(query, data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert price history: {e}")
            return False
    
    async def get_products(self, limit: int = 100, offset: int = 0, filters: Dict[str, Any] = None) -> List[Dict]:
        """Retrieve products from database"""
        try:
            base_query = "SELECT * FROM products WHERE 1=1"
            params = {}
            
            if filters:
                if 'category_id' in filters:
                    base_query += " AND category_id = %(category_id)s"
                    params['category_id'] = filters['category_id']
                
                if 'seller_id' in filters:
                    base_query += " AND seller_id = %(seller_id)s"
                    params['seller_id'] = filters['seller_id']
                
                if 'min_price' in filters:
                    base_query += " AND price >= %(min_price)s"
                    params['min_price'] = filters['min_price']
                
                if 'max_price' in filters:
                    base_query += " AND price <= %(max_price)s"
                    params['max_price'] = filters['max_price']
            
            base_query += f" ORDER BY scraped_at DESC LIMIT {limit} OFFSET {offset}"
            
            result = self.client.execute(base_query, params)
            
            # Convert to list of dictionaries
            columns = [
                'product_id', 'title', 'price', 'original_price', 'discount_percentage',
                'currency', 'shipping_cost', 'free_shipping', 'seller_id', 'seller_name',
                'seller_rating', 'seller_followers', 'category_id', 'category_name',
                'subcategory_id', 'subcategory_name', 'brand', 'sku', 'product_url',
                'image_urls', 'tags', 'specifications', 'total_reviews', 'average_rating',
                'total_sales', 'stock_quantity', 'is_available', 'created_at', 'updated_at',
                'scraped_at', 'seasonal_tags', 'trend_score', 'margin_potential'
            ]
            
            products = []
            for row in result:
                product = dict(zip(columns, row))
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Failed to retrieve products: {e}")
            return []
    
    async def get_product_stats(self) -> Dict[str, Any]:
        """Get overall product statistics"""
        try:
            queries = {
                'total_products': "SELECT count() FROM products",
                'total_categories': "SELECT count(DISTINCT category_id) FROM products",
                'total_sellers': "SELECT count(DISTINCT seller_id) FROM products",
                'avg_price': "SELECT avg(price) FROM products WHERE price > 0",
                'avg_rating': "SELECT avg(average_rating) FROM products WHERE average_rating > 0",
                'total_reviews': "SELECT sum(total_reviews) FROM products"
            }
            
            stats = {}
            for key, query in queries.items():
                result = self.client.execute(query)
                stats[key] = result[0][0] if result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get product stats: {e}")
            return {}
    
    async def get_top_categories(self, limit: int = 10) -> List[Dict]:
        """Get top categories by product count"""
        try:
            query = f"""
            SELECT 
                category_id,
                category_name,
                count() as product_count,
                avg(price) as avg_price,
                avg(average_rating) as avg_rating,
                sum(total_sales) as total_sales
            FROM products 
            GROUP BY category_id, category_name
            ORDER BY product_count DESC
            LIMIT {limit}
            """
            
            result = self.client.execute(query)
            
            categories = []
            for row in result:
                categories.append({
                    'category_id': row[0],
                    'category_name': row[1],
                    'product_count': row[2],
                    'avg_price': float(row[3]) if row[3] else 0,
                    'avg_rating': float(row[4]) if row[4] else 0,
                    'total_sales': row[5]
                })
            
            return categories
            
        except Exception as e:
            logger.error(f"Failed to get top categories: {e}")
            return []
    
    async def get_top_sellers(self, limit: int = 10) -> List[Dict]:
        """Get top sellers by product count and sales"""
        try:
            query = f"""
            SELECT 
                seller_id,
                seller_name,
                count() as product_count,
                avg(seller_rating) as avg_rating,
                sum(total_sales) as total_sales,
                avg(price) as avg_price
            FROM products 
            GROUP BY seller_id, seller_name
            ORDER BY total_sales DESC
            LIMIT {limit}
            """
            
            result = self.client.execute(query)
            
            sellers = []
            for row in result:
                sellers.append({
                    'seller_id': row[0],
                    'seller_name': row[1],
                    'product_count': row[2],
                    'avg_rating': float(row[3]) if row[3] else 0,
                    'total_sales': row[4],
                    'avg_price': float(row[5]) if row[5] else 0
                })
            
            return sellers
            
        except Exception as e:
            logger.error(f"Failed to get top sellers: {e}")
            return []
    
    async def get_price_distribution(self) -> Dict[str, Any]:
        """Get price distribution statistics"""
        try:
            query = """
            SELECT 
                quantile(0.25)(price) as q25,
                quantile(0.5)(price) as median,
                quantile(0.75)(price) as q75,
                quantile(0.9)(price) as q90,
                quantile(0.95)(price) as q95,
                quantile(0.99)(price) as q99,
                min(price) as min_price,
                max(price) as max_price
            FROM products 
            WHERE price > 0
            """
            
            result = self.client.execute(query)
            row = result[0]
            
            return {
                'q25': float(row[0]) if row[0] else 0,
                'median': float(row[1]) if row[1] else 0,
                'q75': float(row[2]) if row[2] else 0,
                'q90': float(row[3]) if row[3] else 0,
                'q95': float(row[4]) if row[4] else 0,
                'q99': float(row[5]) if row[5] else 0,
                'min_price': float(row[6]) if row[6] else 0,
                'max_price': float(row[7]) if row[7] else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get price distribution: {e}")
            return {}
    
    async def get_trending_products(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get trending products based on recent activity"""
        try:
            query = f"""
            SELECT 
                product_id,
                title,
                price,
                average_rating,
                total_reviews,
                total_sales,
                trend_score,
                scraped_at
            FROM products 
            WHERE scraped_at >= now() - INTERVAL {days} DAY
            ORDER BY trend_score DESC, total_sales DESC
            LIMIT {limit}
            """
            
            result = self.client.execute(query)
            
            products = []
            for row in result:
                products.append({
                    'product_id': row[0],
                    'title': row[1],
                    'price': float(row[2]) if row[2] else 0,
                    'average_rating': float(row[3]) if row[3] else 0,
                    'total_reviews': row[4],
                    'total_sales': row[5],
                    'trend_score': float(row[6]) if row[6] else 0,
                    'scraped_at': row[7]
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Failed to get trending products: {e}")
            return []
    
    async def insert_master_product(
        self, 
        product_id: str, 
        product_url: str, 
        category_id: str, 
        category_name: str
    ) -> bool:
        """
        Insert or update a product in the master_products table with UPSERT logic
        
        Args:
            product_id: The product ID
            product_url: Full product URL
            category_id: Category ID where discovered
            category_name: Category name where discovered
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use ReplacingMergeTree INSERT - ClickHouse will handle duplicates
            query = """
            INSERT INTO master_products (
                product_id, product_url, category_id, category_name,
                discovered_at, scrape_status, scrape_priority, error_count, is_active
            ) VALUES (
                %(product_id)s, %(product_url)s, %(category_id)s, %(category_name)s,
                now(), 'pending', 5, 0, 1
            )
            """
            
            self.client.execute(query, {
                'product_id': product_id,
                'product_url': product_url,
                'category_id': category_id,
                'category_name': category_name
            })
            
            logger.debug(f"Inserted master product: {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert master product {product_id}: {e}")
            return False
    
    async def batch_insert_master_products(self, products_list: List[Dict[str, Any]]) -> int:
        """
        Bulk insert discovered product IDs into master_products table
        
        Args:
            products_list: List of dicts with product_id, product_url, category_id, category_name
            
        Returns:
            Number of successfully inserted products
        """
        successful_inserts = 0
        
        for product in products_list:
            if await self.insert_master_product(
                product.get('product_id'),
                product.get('product_url'),
                product.get('category_id', ''),
                product.get('category_name', '')
            ):
                successful_inserts += 1
        
        logger.info(f"Batch inserted {successful_inserts}/{len(products_list)} master products")
        return successful_inserts
    
    async def get_products_to_scrape(
        self, 
        limit: int = 100, 
        priority_threshold: int = 1,
        status_filter: str = 'pending'
    ) -> List[Dict[str, Any]]:
        """
        Query master_products for products needing full scrape
        
        Args:
            limit: Maximum number of products to return
            priority_threshold: Minimum priority level (1-10)
            status_filter: Status to filter by ('pending', 'scraped', 'failed')
            
        Returns:
            List of products with product_id and product_url
        """
        try:
            query = f"""
            SELECT 
                product_id,
                product_url,
                category_id,
                category_name,
                scrape_priority,
                error_count
            FROM master_products
            WHERE scrape_status = %(status_filter)s
                AND scrape_priority >= %(priority_threshold)s
                AND is_active = 1
            ORDER BY scrape_priority DESC, discovered_at ASC
            LIMIT {limit}
            """
            
            result = self.client.execute(query, {
                'status_filter': status_filter,
                'priority_threshold': priority_threshold
            })
            
            products = []
            for row in result:
                products.append({
                    'product_id': row[0],
                    'product_url': row[1],
                    'category_id': row[2],
                    'category_name': row[3],
                    'scrape_priority': row[4],
                    'error_count': row[5]
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Failed to get products to scrape: {e}")
            return []
    
    async def update_scrape_status(
        self, 
        product_id: str, 
        status: str, 
        error_message: str = None
    ) -> bool:
        """
        Update scrape status and error tracking for a product
        
        Args:
            product_id: The product ID
            status: New status ('pending', 'scraped', 'failed', 'skipped')
            error_message: Optional error message for failed scrapes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # If marking as failed, increment error count
            if status == 'failed':
                query = """
                ALTER TABLE master_products UPDATE
                    scrape_status = 'failed',
                    error_count = error_count + 1
                WHERE product_id = %(product_id)s
                """
            elif status == 'scraped':
                query = """
                ALTER TABLE master_products UPDATE
                    scrape_status = 'scraped',
                    last_scraped_at = now()
                WHERE product_id = %(product_id)s
                """
            else:
                query = """
                ALTER TABLE master_products UPDATE
                    scrape_status = %(status)s
                WHERE product_id = %(product_id)s
                """
            
            params = {'product_id': product_id}
            if status != 'failed' and status != 'scraped':
                params['status'] = status
            
            self.client.execute(query, params)
            logger.debug(f"Updated scrape status for {product_id}: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update scrape status for {product_id}: {e}")
            return False
    
    async def mark_inactive_products(self, days_threshold: int = 30) -> int:
        """
        Mark products as inactive if not seen in recent scans
        
        Args:
            days_threshold: Number of days since last discovery
            
        Returns:
            Number of products marked as inactive
        """
        try:
            query = f"""
            ALTER TABLE master_products UPDATE
                is_active = 0
            WHERE discovered_at < now() - INTERVAL {days_threshold} DAY
                AND is_active = 1
                AND scrape_status = 'pending'
            """
            
            self.client.execute(query)
            
            # Count updated rows
            count_query = """
            SELECT count()
            FROM master_products
            WHERE is_active = 0
                AND discovered_at >= now() - INTERVAL 1 HOUR
            """
            
            result = self.client.execute(count_query)
            count = result[0][0] if result else 0
            
            logger.info(f"Marked {count} products as inactive")
            return count
            
        except Exception as e:
            logger.error(f"Failed to mark inactive products: {e}")
            return 0
    
    async def cleanup_failed_products(self, error_threshold: int = 5) -> int:
        """
        Mark products with too many errors as 'skipped'
        
        Args:
            error_threshold: Maximum number of errors before skipping
            
        Returns:
            Number of products marked as skipped
        """
        try:
            query = f"""
            ALTER TABLE master_products UPDATE
                scrape_status = 'skipped'
            WHERE error_count >= {error_threshold}
                AND scrape_status = 'failed'
            """
            
            self.client.execute(query)
            
            # Count updated rows
            count_query = f"""
            SELECT count()
            FROM master_products
            WHERE scrape_status = 'skipped'
                AND error_count >= {error_threshold}
            """
            
            result = self.client.execute(count_query)
            count = result[0][0] if result else 0
            
            logger.info(f"Marked {count} failed products as skipped")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup failed products: {e}")
            return 0
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.disconnect()
        if self.engine:
            try:
                self.engine.dispose()
            except Exception:
                pass  # Engine might not be initialized
        logger.info("Database connection closed")


# Example usage
async def main():
    """Example usage of database operations"""
    db = ClickHouseClient()
    
    # Test connection
    if db.test_connection():
        print("Database connection successful")
    
    # Get product stats
    stats = await db.get_product_stats()
    print(f"Total products: {stats.get('total_products', 0)}")
    
    # Get top categories
    categories = await db.get_top_categories(5)
    for category in categories:
        print(f"Category: {category['category_name']} - {category['product_count']} products")
    
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
