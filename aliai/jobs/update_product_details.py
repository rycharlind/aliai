"""
AliAI - Product Details Update Jobs
Update full product details from master_products table
"""

import asyncio
from typing import List
from loguru import logger
from aliai.scraper import AliExpressScraper
from aliai.database import ClickHouseClient


async def update_products_batch(
    batch_size: int = 100, 
    priority_min: int = 1, 
    status_filter: str = 'pending'
) -> int:
    """
    Update full product details for a batch of products from master table
    
    Args:
        batch_size: Number of products to update
        priority_min: Minimum priority level (1-10)
        status_filter: Status to filter by ('pending', 'scraped', 'failed')
        
    Returns:
        Number of successfully updated products
    """
    logger.info(f"Updating batch of products: batch_size={batch_size}, priority>={priority_min}, status={status_filter}")
    
    try:
        db = ClickHouseClient()
        
        # Get products to scrape from master table
        products_to_scrape = await db.get_products_to_scrape(
            limit=batch_size,
            priority_threshold=priority_min,
            status_filter=status_filter
        )
        
        if not products_to_scrape:
            logger.info("No products found to update")
            db.close()
            return 0
        
        logger.info(f"Found {len(products_to_scrape)} products to update")
        
        successful_updates = 0
        failed_updates = 0
        
        async with AliExpressScraper() as scraper:
            for product_info in products_to_scrape:
                product_id = product_info['product_id']
                product_url = product_info['product_url']
                
                try:
                    # Scrape full product details
                    product_data = await scraper.scrape_product(product_url)
                    
                    if product_data:
                        # Insert full product data into products table
                        success = await db.insert_product(product_data)
                        
                        if success:
                            # Update master table status to 'scraped'
                            await db.update_scrape_status(product_id, 'scraped')
                            successful_updates += 1
                            logger.debug(f"Successfully updated product: {product_id}")
                        else:
                            await db.update_scrape_status(product_id, 'failed')
                            failed_updates += 1
                            logger.warning(f"Failed to insert product data: {product_id}")
                    else:
                        # Mark as failed if scraping returned None
                        await db.update_scrape_status(product_id, 'failed')
                        failed_updates += 1
                        logger.warning(f"Failed to scrape product: {product_id}")
                    
                    # Small delay between products
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error updating product {product_id}: {e}")
                    await db.update_scrape_status(product_id, 'failed')
                    failed_updates += 1
        
        db.close()
        logger.info(f"Batch update complete: {successful_updates} successful, {failed_updates} failed")
        return successful_updates
        
    except Exception as e:
        logger.error(f"Error during batch update: {e}")
        return 0


async def update_single_product(product_id: str) -> bool:
    """
    Update a single product by ID from master table
    
    Args:
        product_id: The product ID to update
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Updating single product: {product_id}")
    
    try:
        db = ClickHouseClient()
        
        # Get product URL from master table
        query = """
        SELECT product_url
        FROM master_products
        WHERE product_id = %(product_id)s
        LIMIT 1
        """
        
        result = db.client.execute(query, {'product_id': product_id})
        
        if not result:
            logger.warning(f"Product {product_id} not found in master table")
            db.close()
            return False
        
        product_url = result[0][0]
        
        # Scrape full product details
        async with AliExpressScraper() as scraper:
            product_data = await scraper.scrape_product(product_url)
            
            if product_data:
                # Insert full product data
                success = await db.insert_product(product_data)
                
                if success:
                    await db.update_scrape_status(product_id, 'scraped')
                    logger.info(f"Successfully updated product: {product_id}")
                    db.close()
                    return True
                else:
                    await db.update_scrape_status(product_id, 'failed')
                    logger.warning(f"Failed to insert product data: {product_id}")
            else:
                await db.update_scrape_status(product_id, 'failed')
                logger.warning(f"Failed to scrape product: {product_id}")
        
        db.close()
        return False
        
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        return False


async def update_high_priority_products(limit: int = 50) -> int:
    """
    Update high-priority products (priority >= 8) first
    
    Args:
        limit: Number of high-priority products to update
        
    Returns:
        Number of successfully updated products
    """
    logger.info(f"Updating {limit} high-priority products")
    
    # Only update products with priority >= 8
    return await update_products_batch(
        batch_size=limit,
        priority_min=8,
        status_filter='pending'
    )


if __name__ == "__main__":
    # Example usage
    async def main():
        # Update a batch of products
        count = await update_products_batch(batch_size=10, priority_min=1)
        print(f"Updated {count} products")
        
        # Update high-priority products
        # count = await update_high_priority_products(limit=20)
        # print(f"Updated {count} high-priority products")
        
        # Update a single product
        # success = await update_single_product("3256810016116999")
        # print(f"Update successful: {success}")
    
    asyncio.run(main())

