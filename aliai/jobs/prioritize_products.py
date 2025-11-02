"""
AliAI - Product Prioritization Jobs
Calculate and update product priorities for scraping
"""

import asyncio
from loguru import logger
from aliai.database import ClickHouseClient


async def calculate_priorities() -> int:
    """
    Calculate scrape_priority based on product metrics
    
    Priority calculation:
    - Higher priority for trending products (recent sales activity)
    - Higher priority for high-sales products
    - Higher priority for products with good ratings
    - Lower priority for products that failed multiple times
    
    Returns:
        Number of products with updated priorities
    """
    logger.info("Calculating product priorities")
    
    try:
        db = ClickHouseClient()
        
        # Update priorities based on various metrics
        # This is a simplified version - can be expanded with more sophisticated logic
        
        # Boost priority for products in trending/active categories
        category_boost_query = """
        ALTER TABLE master_products UPDATE
            scrape_priority = least(scrape_priority + 2, 10)
        WHERE category_id IN (
            SELECT category_id
            FROM products
            WHERE scraped_at >= now() - INTERVAL 7 DAY
            GROUP BY category_id
            HAVING count() > 100
        )
        AND scrape_status = 'pending'
        """
        
        db.client.execute(category_boost_query)
        
        # Lower priority for products with too many errors
        error_penalty_query = """
        ALTER TABLE master_products UPDATE
            scrape_priority = greatest(scrape_priority - 1, 1)
        WHERE error_count >= 3
        AND scrape_status = 'pending'
        """
        
        db.client.execute(error_penalty_query)
        
        # Boost priority for recently discovered products (might be new/trending)
        new_product_boost_query = """
        ALTER TABLE master_products UPDATE
            scrape_priority = 8
        WHERE discovered_at >= now() - INTERVAL 1 DAY
        AND scrape_status = 'pending'
        AND scrape_priority < 8
        """
        
        db.client.execute(new_product_boost_query)
        
        # Count updated products
        count_query = """
        SELECT count()
        FROM master_products
        WHERE last_scraped_at >= now() - INTERVAL 1 HOUR
        """
        
        result = db.client.execute(count_query)
        count = result[0][0] if result else 0
        
        db.close()
        logger.info(f"Updated priorities for products")
        return count
        
    except Exception as e:
        logger.error(f"Error calculating priorities: {e}")
        return 0


async def boost_category_priority(category_id: str, boost_amount: int = 2) -> int:
    """
    Increase priority for all products in a specific category
    
    Args:
        category_id: The category ID to boost
        boost_amount: Amount to increase priority (will cap at 10)
        
    Returns:
        Number of products with boosted priority
    """
    logger.info(f"Boosting priority for category: {category_id} by {boost_amount}")
    
    try:
        db = ClickHouseClient()
        
        query = f"""
        ALTER TABLE master_products UPDATE
            scrape_priority = least(scrape_priority + {boost_amount}, 10)
        WHERE category_id = %(category_id)s
        AND scrape_status = 'pending'
        AND is_active = 1
        """
        
        db.client.execute(query, {'category_id': category_id})
        
        # Count updated products
        count_query = """
        SELECT count()
        FROM master_products
        WHERE category_id = %(category_id)s
        AND last_scraped_at >= now() - INTERVAL 1 HOUR
        """
        
        result = db.client.execute(count_query, {'category_id': category_id})
        count = result[0][0] if result else 0
        
        db.close()
        logger.info(f"Boosted priority for {count} products in category {category_id}")
        return count
        
    except Exception as e:
        logger.error(f"Error boosting category priority: {e}")
        return 0


if __name__ == "__main__":
    # Example usage
    async def main():
        # Calculate all priorities
        # count = await calculate_priorities()
        # print(f"Updated priorities for products")
        
        # Boost a specific category
        count = await boost_category_priority("100003070", boost_amount=2)
        print(f"Boosted {count} products")
    
    asyncio.run(main())

