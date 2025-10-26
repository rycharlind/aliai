"""
AliAI - Main Application Entry Point
Orchestrates the complete scraping and analysis pipeline
"""

import asyncio
import argparse
import sys
from typing import List, Dict, Any
from loguru import logger
from aliai.config import get_config
from aliai.scraper import AliExpressScraper
from aliai.ai_processor import AIProcessor
from aliai.database import ClickHouseClient
from aliai.analytics import AnalyticsEngine


class AliAIApp:
    """Main application class"""
    
    def __init__(self):
        self.config = get_config()
        self.scraper = None
        self.ai_processor = AIProcessor()
        self.db = ClickHouseClient()
        self.analytics = AnalyticsEngine()
        
        # Configure logging
        logger.remove()
        logger.add(
            sys.stdout,
            level=self.config.monitoring.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
    
    async def scrape_products(self, category_urls: List[str] = None, search_terms: List[str] = None, max_pages: int = 5) -> int:
        """Scrape products from categories or search terms"""
        if not category_urls and not search_terms:
            # Default categories
            category_urls = [
                "https://www.aliexpress.com/category/100003070/electronics.html",
                "https://www.aliexpress.com/category/100003109/clothing.html",
                "https://www.aliexpress.com/category/100003109/home-garden.html"
            ]
        
        total_scraped = 0
        
        async with AliExpressScraper() as scraper:
            # Scrape categories
            if category_urls:
                for category_url in category_urls:
                    try:
                        logger.info(f"Scraping category: {category_url}")
                        products = await scraper.scrape_category(category_url, max_pages)
                        if products:
                            inserted = await self.db.batch_insert_products(products)
                            total_scraped += inserted
                            logger.info(f"Scraped {inserted} products from category")
                    except Exception as e:
                        logger.error(f"Error scraping category {category_url}: {e}")
            
            # Scrape search terms
            if search_terms:
                for search_term in search_terms:
                    try:
                        logger.info(f"Scraping search: {search_term}")
                        products = await scraper.scrape_search_results(search_term, max_pages)
                        if products:
                            inserted = await self.db.batch_insert_products(products)
                            total_scraped += inserted
                            logger.info(f"Scraped {inserted} products for '{search_term}'")
                    except Exception as e:
                        logger.error(f"Error scraping search '{search_term}': {e}")
        
        logger.info(f"Total products scraped: {total_scraped}")
        return total_scraped
    
    async def analyze_data(self) -> Dict[str, Any]:
        """Perform AI analysis on scraped data"""
        logger.info("Starting AI analysis...")
        
        # Get recent products without AI processing
        products = await self.db.get_products(limit=1000)
        
        processed_count = 0
        
        for product in products:
            try:
                # Categorize product
                category = await self.ai_processor.process_product(
                    product['title'],
                    product.get('description', ''),
                    product.get('tags', [])
                )
                
                # Update product with AI analysis
                update_query = """
                ALTER TABLE products UPDATE 
                    category_id = %(category_id)s,
                    category_name = %(category_name)s,
                    seasonal_tags = %(seasonal_tags)s,
                    trend_score = %(trend_score)s
                WHERE product_id = %(product_id)s
                """
                
                self.db.client.execute(update_query, {
                    'category_id': category.category_id,
                    'category_name': category.category_name,
                    'seasonal_tags': category.seasonal_tags,
                    'trend_score': category.confidence,
                    'product_id': product['product_id']
                })
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing product {product['product_id']}: {e}")
        
        logger.info(f"AI processed {processed_count} products")
        return {'processed_products': processed_count}
    
    async def generate_insights(self) -> Dict[str, Any]:
        """Generate business insights and reports"""
        logger.info("Generating business insights...")
        
        try:
            # Generate comprehensive report
            report = await self.analytics.generate_business_report()
            
            # Extract key insights
            insights = {
                'market_overview': report.get('executive_summary', {}),
                'top_opportunities': report.get('opportunities', {}).get('high_margin_products', [])[:10],
                'trending_products': report.get('opportunities', {}).get('trending_products', [])[:10],
                'recommendations': report.get('recommendations', [])[:5]
            }
            
            logger.info("Business insights generated successfully")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {}
    
    async def run_full_pipeline(self) -> Dict[str, Any]:
        """Run the complete scraping and analysis pipeline"""
        logger.info("Starting full AliAI pipeline...")
        
        results = {}
        
        try:
            # Step 1: Scrape products
            logger.info("Step 1: Scraping products...")
            scraped_count = await self.scrape_products()
            results['scraped_products'] = scraped_count
            
            # Step 2: AI Analysis
            logger.info("Step 2: AI analysis...")
            analysis_results = await self.analyze_data()
            results.update(analysis_results)
            
            # Step 3: Generate insights
            logger.info("Step 3: Generating insights...")
            insights = await self.generate_insights()
            results['insights'] = insights
            
            logger.info("Full pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def close(self):
        """Close all connections"""
        self.db.close()
        self.analytics.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AliAI - AliExpress Scraping & Analysis System')
    parser.add_argument('--mode', choices=['scrape', 'analyze', 'insights', 'full'], 
                       default='full', help='Operation mode')
    parser.add_argument('--categories', nargs='+', help='Category URLs to scrape')
    parser.add_argument('--search', nargs='+', help='Search terms to scrape')
    parser.add_argument('--pages', type=int, default=5, help='Maximum pages to scrape')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG")
    
    app = AliAIApp()
    
    try:
        if args.mode == 'scrape':
            await app.scrape_products(args.categories, args.search, args.pages)
        elif args.mode == 'analyze':
            await app.analyze_data()
        elif args.mode == 'insights':
            insights = await app.generate_insights()
            print("\n=== BUSINESS INSIGHTS ===")
            print(f"Total Products: {insights.get('market_overview', {}).get('total_products_analyzed', 0)}")
            print(f"Total Categories: {insights.get('market_overview', {}).get('total_categories', 0)}")
            
            print("\n=== TOP OPPORTUNITIES ===")
            for i, opp in enumerate(insights.get('top_opportunities', [])[:5], 1):
                print(f"{i}. {opp['title'][:60]}... - Score: {opp['margin_potential_score']}")
            
            print("\n=== RECOMMENDATIONS ===")
            for i, rec in enumerate(insights.get('recommendations', [])[:3], 1):
                print(f"{i}. {rec}")
        else:  # full
            results = await app.run_full_pipeline()
            print(f"\nPipeline Results:")
            print(f"Scraped Products: {results.get('scraped_products', 0)}")
            print(f"Processed Products: {results.get('processed_products', 0)}")
            
            if 'insights' in results:
                insights = results['insights']
                print(f"Total Products Analyzed: {insights.get('market_overview', {}).get('total_products_analyzed', 0)}")
                print(f"Top Opportunities Found: {len(insights.get('top_opportunities', []))}")
    
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
    finally:
        app.close()


if __name__ == "__main__":
    asyncio.run(main())
