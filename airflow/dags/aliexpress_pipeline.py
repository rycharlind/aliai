"""
AliAI - Airflow DAGs for Automated Scraping Pipeline
Handles scheduled scraping, AI processing, and data analysis
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.models import Variable
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append('/Users/ryanlindbeck/Development/aliai')

from aliai.scraper import AliExpressScraper
from aliai.ai_processor import AIProcessor
from aliai.database import ClickHouseClient
from aliai.analytics import AnalyticsEngine


# Default arguments for DAGs
default_args = {
    'owner': 'aliai',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Define DAG for daily scraping
scraping_dag = DAG(
    'aliexpress_daily_scraping',
    default_args=default_args,
    description='Daily AliExpress product scraping and analysis',
    schedule='0 2 * * *',  # Run daily at 2 AM
    max_active_runs=1,
    tags=['scraping', 'aliexpress', 'daily']
)

# Define DAG for weekly analysis
analysis_dag = DAG(
    'aliexpress_weekly_analysis',
    default_args=default_args,
    description='Weekly business intelligence analysis',
    schedule='0 6 * * 1',  # Run weekly on Monday at 6 AM
    max_active_runs=1,
    tags=['analysis', 'business-intelligence', 'weekly']
)

# Define DAG for real-time monitoring
monitoring_dag = DAG(
    'aliexpress_monitoring',
    default_args=default_args,
    description='Real-time monitoring and health checks',
    schedule='*/15 * * * *',  # Run every 15 minutes
    max_active_runs=1,
    tags=['monitoring', 'health-checks', 'real-time']
)


def scrape_popular_categories():
    """Scrape popular product categories"""
    async def _scrape_categories():
        categories = [
            "https://www.aliexpress.com/category/100003070/electronics.html",
            "https://www.aliexpress.com/category/100003109/clothing.html",
            "https://www.aliexpress.com/category/100003109/home-garden.html",
            "https://www.aliexpress.com/category/100003109/beauty-health.html",
            "https://www.aliexpress.com/category/100003109/sports-outdoors.html"
        ]
        
        scraper = AliExpressScraper()
        db = ClickHouseClient()
        
        total_products = 0
        
        async with scraper:
            for category_url in categories:
                try:
                    products = await scraper.scrape_category(category_url, max_pages=5)
                    if products:
                        inserted = await db.batch_insert_products(products)
                        total_products += inserted
                        print(f"Scraped {inserted} products from {category_url}")
                except Exception as e:
                    print(f"Error scraping {category_url}: {e}")
        
        db.close()
        print(f"Total products scraped: {total_products}")
        return total_products
    
    return asyncio.run(_scrape_categories())


def scrape_trending_products():
    """Scrape trending products from search results"""
    async def _scrape_trending():
        trending_searches = [
            "wireless headphones",
            "phone case",
            "led lights",
            "kitchen gadgets",
            "fitness tracker",
            "bluetooth speaker",
            "car accessories",
            "home decoration"
        ]
        
        scraper = AliExpressScraper()
        db = ClickHouseClient()
        
        total_products = 0
        
        async with scraper:
            for search_term in trending_searches:
                try:
                    products = await scraper.scrape_search_results(search_term, max_pages=3)
                    if products:
                        inserted = await db.batch_insert_products(products)
                        total_products += inserted
                        print(f"Scraped {inserted} products for '{search_term}'")
                except Exception as e:
                    print(f"Error scraping '{search_term}': {e}")
        
        db.close()
        print(f"Total trending products scraped: {total_products}")
        return total_products
    
    return asyncio.run(_scrape_trending())


def process_ai_analysis():
    """Process scraped products with AI analysis"""
    async def _process_ai():
        db = ClickHouseClient()
        ai_processor = AIProcessor()
        
        # Get recent products without AI processing
        products = await db.get_products(limit=1000, filters={'ai_processed': False})
        
        processed_count = 0
        
        for product in products:
            try:
                # Categorize product
                category = await ai_processor.process_product(
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
                
                db.client.execute(update_query, {
                    'category_id': category.category_id,
                    'category_name': category.category_name,
                    'seasonal_tags': category.seasonal_tags,
                    'trend_score': category.confidence,
                    'product_id': product['product_id']
                })
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error processing product {product['product_id']}: {e}")
        
        db.close()
        print(f"AI processed {processed_count} products")
        return processed_count
    
    return asyncio.run(_process_ai())


def analyze_sentiment():
    """Analyze sentiment of product reviews"""
    async def _analyze_sentiment():
        db = ClickHouseClient()
        ai_processor = AIProcessor()
        
        # Get recent reviews without sentiment analysis
        query = """
        SELECT review_id, product_id, review_text, rating
        FROM reviews 
        WHERE sentiment_score IS NULL
        LIMIT 500
        """
        
        result = db.client.execute(query)
        
        processed_count = 0
        
        for row in result:
            try:
                review_id, product_id, review_text, rating = row
                
                # Analyze sentiment
                sentiment = await ai_processor.process_review(review_text)
                
                # Update review with sentiment analysis
                update_query = """
                ALTER TABLE reviews UPDATE 
                    sentiment_score = %(sentiment_score)s,
                    sentiment_label = %(sentiment_label)s,
                    key_phrases = %(key_phrases)s,
                    language = %(language)s
                WHERE review_id = %(review_id)s
                """
                
                db.client.execute(update_query, {
                    'sentiment_score': sentiment.sentiment_score,
                    'sentiment_label': sentiment.sentiment_label,
                    'key_phrases': sentiment.key_phrases,
                    'language': sentiment.language,
                    'review_id': review_id
                })
                
                processed_count += 1
                
            except Exception as e:
                print(f"Error analyzing sentiment for review {row[0]}: {e}")
        
        db.close()
        print(f"Sentiment analyzed for {processed_count} reviews")
        return processed_count
    
    return asyncio.run(_analyze_sentiment())


def generate_business_report():
    """Generate comprehensive business intelligence report"""
    async def _generate_report():
        analytics = AnalyticsEngine()
        
        try:
            report = await analytics.generate_business_report()
            
            # Save report to file
            report_file = f"/tmp/aliexpress_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            import json
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"Business report generated: {report_file}")
            
            # Store key metrics in Airflow variables
            if report.get('executive_summary'):
                summary = report['executive_summary']
                Variable.set("total_products", summary.get('total_products_analyzed', 0))
                Variable.set("total_categories", summary.get('total_categories', 0))
                Variable.set("avg_market_price", summary.get('avg_market_price', 0))
            
            analytics.close()
            return report_file
            
        except Exception as e:
            print(f"Error generating business report: {e}")
            analytics.close()
            return None
    
    return asyncio.run(_generate_report())


def detect_trends():
    """Detect trending products and categories"""
    async def _detect_trends():
        analytics = AnalyticsEngine()
        
        try:
            # Get trending products
            trending_products = await analytics.get_trending_products(days=7, limit=50)
            
            # Get high margin opportunities
            opportunities = await analytics.detect_high_margin_opportunities()
            
            # Store trends in database
            db = ClickHouseClient()
            
            for product in trending_products:
                trend_data = {
                    'trend_id': f"trend_{product['product_id']}_{datetime.now().strftime('%Y%m%d')}",
                    'product_id': product['product_id'],
                    'category_id': product.get('category_id', 'unknown'),
                    'trend_type': 'viral',
                    'trend_score': product['trend_score'],
                    'trend_direction': 'up',
                    'confidence_score': min(product['trend_score'] * 2, 1.0),
                    'detected_at': datetime.now(),
                    'duration_days': 7,
                    'peak_score': product['trend_score']
                }
                
                insert_query = """
                INSERT INTO trends (
                    trend_id, product_id, category_id, trend_type,
                    trend_score, trend_direction, confidence_score,
                    detected_at, duration_days, peak_score, created_at
                ) VALUES (
                    %(trend_id)s, %(product_id)s, %(category_id)s, %(trend_type)s,
                    %(trend_score)s, %(trend_direction)s, %(confidence_score)s,
                    %(detected_at)s, %(duration_days)s, %(peak_score)s, %(created_at)s
                )
                """
                
                trend_data['created_at'] = datetime.now()
                db.client.execute(insert_query, trend_data)
            
            db.close()
            analytics.close()
            
            print(f"Detected {len(trending_products)} trending products")
            print(f"Found {len(opportunities)} high-margin opportunities")
            
            return len(trending_products)
            
        except Exception as e:
            print(f"Error detecting trends: {e}")
            analytics.close()
            return 0
    
    return asyncio.run(_detect_trends())


def health_check():
    """Perform system health checks"""
    async def _health_check():
        db = ClickHouseClient()
        
        try:
            # Test database connection
            if not db.test_connection():
                print("❌ Database connection failed")
                return False
            
            # Check recent data
            stats = await db.get_product_stats()
            recent_products = await db.get_products(limit=10)
            
            if stats.get('total_products', 0) == 0:
                print("❌ No products found in database")
                return False
            
            if not recent_products:
                print("❌ No recent products found")
                return False
            
            print("✅ System health check passed")
            print(f"   Total products: {stats.get('total_products', 0)}")
            print(f"   Recent products: {len(recent_products)}")
            
            db.close()
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            db.close()
            return False
    
    return asyncio.run(_health_check())


def cleanup_old_data():
    """Clean up old data to maintain performance"""
    async def _cleanup():
        db = ClickHouseClient()
        
        try:
            # Delete old scraping logs (older than 30 days)
            cleanup_query = """
            ALTER TABLE scraping_logs DELETE 
            WHERE scraped_at < now() - INTERVAL 30 DAY
            """
            
            db.client.execute(cleanup_query)
            
            # Delete old price history (older than 90 days)
            cleanup_query = """
            ALTER TABLE price_history DELETE 
            WHERE scraped_at < now() - INTERVAL 90 DAY
            """
            
            db.client.execute(cleanup_query)
            
            print("✅ Old data cleanup completed")
            db.close()
            return True
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            db.close()
            return False
    
    return asyncio.run(_cleanup())


# Daily Scraping Tasks
scrape_categories_task = PythonOperator(
    task_id='scrape_popular_categories',
    python_callable=scrape_popular_categories,
    dag=scraping_dag
)

scrape_trending_task = PythonOperator(
    task_id='scrape_trending_products',
    python_callable=scrape_trending_products,
    dag=scraping_dag
)

process_ai_task = PythonOperator(
    task_id='process_ai_analysis',
    python_callable=process_ai_analysis,
    dag=scraping_dag
)

analyze_sentiment_task = PythonOperator(
    task_id='analyze_sentiment',
    python_callable=analyze_sentiment,
    dag=scraping_dag
)

# Weekly Analysis Tasks
generate_report_task = PythonOperator(
    task_id='generate_business_report',
    python_callable=generate_business_report,
    dag=analysis_dag
)

detect_trends_task = PythonOperator(
    task_id='detect_trends',
    python_callable=detect_trends,
    dag=analysis_dag
)

# Monitoring Tasks
health_check_task = PythonOperator(
    task_id='health_check',
    python_callable=health_check,
    dag=monitoring_dag
)

cleanup_task = PythonOperator(
    task_id='cleanup_old_data',
    python_callable=cleanup_old_data,
    dag=monitoring_dag
)

# Task Dependencies
scrape_categories_task >> process_ai_task
scrape_trending_task >> process_ai_task
process_ai_task >> analyze_sentiment_task

generate_report_task >> detect_trends_task

health_check_task >> cleanup_task
