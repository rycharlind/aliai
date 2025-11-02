"""
AliAI - Master Table Refresh Jobs
Maintain and refresh the master_products table
"""

import asyncio
from typing import List
from loguru import logger
from aliai.scraper import AliExpressScraper
from aliai.database import ClickHouseClient
from aliai.categories import ALIEXPRESS_CATEGORIES
from aliai.jobs.discover_product_ids import discover_category_ids


async def refresh_category(category_url: str) -> int:
    """
    Re-scan a category to find new products and update existing ones
    
    Args:
        category_url: URL of the category to refresh
        
    Returns:
        Number of new products discovered
    """
    logger.info(f"Refreshing category: {category_url}")
    
    # Use the discovery function to find new products
    # This will update existing products and add new ones
    count = await discover_category_ids(category_url=category_url, max_pages=10)
    logger.info(f"Category refresh complete: {count} new products")
    return count


async def mark_inactive_products(days_threshold: int = 30) -> int:
    """
    Mark products as inactive if not seen in recent scans
    
    Args:
        days_threshold: Number of days since last discovery
        
    Returns:
        Number of products marked as inactive
    """
    logger.info(f"Marking inactive products (older than {days_threshold} days)")
    
    try:
        db = ClickHouseClient()
        count = await db.mark_inactive_products(days_threshold=days_threshold)
        db.close()
        return count
        
    except Exception as e:
        logger.error(f"Error marking inactive products: {e}")
        return 0


async def cleanup_failed_products(error_threshold: int = 5) -> int:
    """
    Mark products with too many errors as 'skipped'
    
    Args:
        error_threshold: Maximum number of errors before skipping
        
    Returns:
        Number of products marked as skipped
    """
    logger.info(f"Cleaning up failed products (error_count >= {error_threshold})")
    
    try:
        db = ClickHouseClient()
        count = await db.cleanup_failed_products(error_threshold=error_threshold)
        db.close()
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up failed products: {e}")
        return 0


async def refresh_all_categories() -> dict:
    """
    Refresh all configured categories to find new products
    
    Returns:
        Dictionary mapping category_name -> count of new products
    """
    logger.info("Refreshing all categories")
    
    results = {}
    top_level_categories = [cat for cat in ALIEXPRESS_CATEGORIES if not cat.parent_id]
    
    for category in top_level_categories:
        try:
            count = await refresh_category(category.url)
            results[category.category_name] = count
            logger.info(f"Refreshed '{category.category_name}': {count} new products")
            
            # Small delay between categories
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error refreshing category {category.category_name}: {e}")
            results[category.category_name] = 0
    
    logger.info("All categories refreshed")
    return results


if __name__ == "__main__":
    # Example usage
    async def main():
        # Refresh a single category
        # count = await refresh_category("https://www.aliexpress.com/category/100003070/electronics.html")
        # print(f"Refreshed {count} products")
        
        # Mark inactive products
        # count = await mark_inactive_products(days_threshold=30)
        # print(f"Marked {count} products as inactive")
        
        # Cleanup failed products
        count = await cleanup_failed_products(error_threshold=5)
        print(f"Cleaned up {count} failed products")
        
        # Refresh all categories
        # results = await refresh_all_categories()
        # print(f"Results: {results}")
    
    asyncio.run(main())

