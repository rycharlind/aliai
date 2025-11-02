"""
AliAI - Product ID Discovery Jobs
Discover product IDs from category listing pages
"""

import asyncio
from typing import Dict, List
from loguru import logger
from aliai.scraper import AliExpressScraper
from aliai.database import ClickHouseClient
from aliai.categories import ALIEXPRESS_CATEGORIES


async def discover_category_ids(category_url: str, max_pages: int = 10) -> int:
    """
    Discover product IDs from a single category and save to master_products table
    
    Args:
        category_url: URL of the category page to scan
        max_pages: Maximum number of pages to scan per category
        
    Returns:
        Number of new products discovered and inserted
    """
    logger.info(f"Starting discovery for category: {category_url}")
    
    try:
        # Extract category info from URL
        category_id = ""
        category_name = ""
        
        # Try to match category from our predefined list
        for cat in ALIEXPRESS_CATEGORIES:
            if cat.url in category_url:
                category_id = cat.category_id
                category_name = cat.category_name
                break
        
        # Initialize scraper and database
        db = ClickHouseClient()
        async with AliExpressScraper() as scraper:
            # Discover product IDs
            discovered_products = await scraper.scrape_category_for_ids(
                category_url=category_url,
                max_pages=max_pages,
                category_id=category_id,
                category_name=category_name
            )
            
            if not discovered_products:
                logger.warning(f"No products discovered from {category_url}")
                db.close()
                return 0
            
            # Prepare data for batch insert
            products_data = [
                {
                    'product_id': p.product_id,
                    'product_url': p.product_url,
                    'category_id': p.category_id,
                    'category_name': p.category_name
                }
                for p in discovered_products
            ]
            
            # Batch insert into master_products table
            inserted_count = await db.batch_insert_master_products(products_data)
            
            db.close()
            logger.info(f"Discovery complete: {inserted_count} new products inserted")
            return inserted_count
            
    except Exception as e:
        logger.error(f"Error during category discovery: {e}")
        return 0


async def discover_all_category_ids(max_pages_per_category: int = 10) -> Dict[str, int]:
    """
    Discover product IDs from all configured categories
    
    Args:
        max_pages_per_category: Maximum number of pages to scan per category
        
    Returns:
        Dictionary mapping category_name -> count of discovered products
    """
    logger.info("Starting discovery for all categories")
    
    results = {}
    total_discovered = 0
    
    # Get top-level categories to avoid duplicates
    top_level_categories = [cat for cat in ALIEXPRESS_CATEGORIES if not cat.parent_id]
    
    for category in top_level_categories:
        try:
            count = await discover_category_ids(
                category_url=category.url,
                max_pages=max_pages_per_category
            )
            results[category.category_name] = count
            total_discovered += count
            logger.info(f"Category '{category.category_name}': {count} products")
            
            # Small delay between categories
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error discovering category {category.category_name}: {e}")
            results[category.category_name] = 0
    
    logger.info(f"Total discovery complete: {total_discovered} products across all categories")
    return results


if __name__ == "__main__":
    # Example usage
    async def main():
        # Discover from a specific category
        count = await discover_category_ids(
            "https://www.aliexpress.com/category/100003070/electronics.html",
            max_pages=3
        )
        print(f"Discovered {count} products")
        
        # Or discover from all categories
        # results = await discover_all_category_ids(max_pages_per_category=5)
        # print(f"Results: {results}")
    
    asyncio.run(main())

