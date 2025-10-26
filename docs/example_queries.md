# AliAI - Example Queries and Analytics

This document provides example ClickHouse queries and analytics examples for the AliAI system.

## Table of Contents
1. [Basic Product Queries](#basic-product-queries)
2. [Market Analysis Queries](#market-analysis-queries)
3. [Trend Analysis Queries](#trend-analysis-queries)
4. [Business Intelligence Queries](#business-intelligence-queries)
5. [Seasonal Analysis Queries](#seasonal-analysis-queries)
6. [Competitor Analysis Queries](#competitor-analysis-queries)
7. [Python Analytics Examples](#python-analytics-examples)

## Basic Product Queries

### Get Total Number of Products
```sql
SELECT count() as total_products FROM products;
```

### Get Products by Category
```sql
SELECT 
    category_name,
    count() as product_count,
    avg(price) as avg_price,
    avg(average_rating) as avg_rating
FROM products 
GROUP BY category_name
ORDER BY product_count DESC;
```

### Get Top Rated Products
```sql
SELECT 
    product_id,
    title,
    price,
    average_rating,
    total_reviews,
    seller_name
FROM products 
WHERE average_rating >= 4.5 
    AND total_reviews >= 50
ORDER BY average_rating DESC, total_reviews DESC
LIMIT 20;
```

### Get Products with Best Price-Performance Ratio
```sql
SELECT 
    product_id,
    title,
    price,
    average_rating,
    (average_rating / price) as rating_per_dollar,
    seller_name
FROM products 
WHERE price > 0 
    AND average_rating > 0
ORDER BY rating_per_dollar DESC
LIMIT 20;
```

## Market Analysis Queries

### Price Distribution Analysis
```sql
SELECT 
    quantile(0.25)(price) as q25_price,
    quantile(0.5)(price) as median_price,
    quantile(0.75)(price) as q75_price,
    quantile(0.9)(price) as q90_price,
    quantile(0.95)(price) as q95_price,
    min(price) as min_price,
    max(price) as max_price,
    avg(price) as avg_price
FROM products 
WHERE price > 0;
```

### Category Market Share
```sql
SELECT 
    category_name,
    count() as product_count,
    sum(total_sales) as total_sales,
    avg(price) as avg_price,
    (count() * 100.0 / (SELECT count() FROM products)) as market_share_percent
FROM products 
GROUP BY category_name
ORDER BY market_share_percent DESC;
```

### Seller Performance Analysis
```sql
SELECT 
    seller_name,
    count() as product_count,
    avg(seller_rating) as avg_seller_rating,
    sum(total_sales) as total_sales,
    avg(price) as avg_price,
    avg(average_rating) as avg_product_rating
FROM products 
GROUP BY seller_name
HAVING product_count >= 10
ORDER BY total_sales DESC
LIMIT 20;
```

## Trend Analysis Queries

### Trending Products (Last 7 Days)
```sql
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
WHERE scraped_at >= now() - INTERVAL 7 DAY
    AND trend_score > 0.5
ORDER BY trend_score DESC, total_sales DESC
LIMIT 20;
```

### Price Trend Analysis
```sql
SELECT 
    product_id,
    title,
    price,
    original_price,
    discount_percentage,
    scraped_at
FROM products 
WHERE scraped_at >= now() - INTERVAL 30 DAY
    AND discount_percentage > 20
ORDER BY discount_percentage DESC
LIMIT 20;
```

### New Arrivals
```sql
SELECT 
    product_id,
    title,
    price,
    average_rating,
    seller_name,
    scraped_at
FROM products 
WHERE scraped_at >= now() - INTERVAL 3 DAY
    AND total_reviews < 10
ORDER BY scraped_at DESC
LIMIT 20;
```

## Business Intelligence Queries

### High-Margin Opportunities
```sql
SELECT 
    product_id,
    title,
    price,
    original_price,
    discount_percentage,
    average_rating,
    total_reviews,
    total_sales,
    seller_name,
    category_name,
    -- Calculate margin potential score
    (average_rating * 0.3 + 
     (total_sales / 1000.0) * 0.3 + 
     (100 - price) * 0.2 + 
     (total_reviews / 100.0) * 0.2) as margin_potential_score
FROM products 
WHERE average_rating >= 4.0
    AND price <= 100
    AND total_reviews >= 10
    AND total_sales > 0
ORDER BY margin_potential_score DESC
LIMIT 50;
```

### Best Selling Categories
```sql
SELECT 
    category_name,
    count() as product_count,
    sum(total_sales) as total_sales,
    avg(price) as avg_price,
    avg(average_rating) as avg_rating,
    sum(total_reviews) as total_reviews
FROM products 
GROUP BY category_name
ORDER BY total_sales DESC
LIMIT 15;
```

### Shipping Analysis
```sql
SELECT 
    CASE 
        WHEN free_shipping = 1 THEN 'Free Shipping'
        WHEN shipping_cost = 0 THEN 'No Shipping Cost'
        WHEN shipping_cost <= 5 THEN 'Low Shipping ($0-5)'
        WHEN shipping_cost <= 15 THEN 'Medium Shipping ($5-15)'
        ELSE 'High Shipping ($15+)'
    END as shipping_category,
    count() as product_count,
    avg(price) as avg_price,
    avg(average_rating) as avg_rating
FROM products 
GROUP BY shipping_category
ORDER BY product_count DESC;
```

## Seasonal Analysis Queries

### Seasonal Product Distribution
```sql
SELECT 
    arrayJoin(seasonal_tags) as season,
    count() as product_count,
    avg(price) as avg_price,
    sum(total_sales) as total_sales
FROM products 
WHERE seasonal_tags != []
GROUP BY season
ORDER BY product_count DESC;
```

### Holiday Season Analysis
```sql
SELECT 
    category_name,
    count() as product_count,
    avg(price) as avg_price,
    sum(total_sales) as total_sales
FROM products 
WHERE has(seasonal_tags, 'christmas') 
    OR has(seasonal_tags, 'halloween')
GROUP BY category_name
ORDER BY total_sales DESC
LIMIT 20;
```

### Seasonal Price Trends
```sql
SELECT 
    arrayJoin(seasonal_tags) as season,
    quantile(0.5)(price) as median_price,
    quantile(0.25)(price) as q25_price,
    quantile(0.75)(price) as q75_price,
    count() as product_count
FROM products 
WHERE seasonal_tags != []
GROUP BY season
ORDER BY median_price DESC;
```

## Competitor Analysis Queries

### Top Competitors by Category
```sql
SELECT 
    category_name,
    seller_name,
    count() as product_count,
    avg(price) as avg_price,
    avg(average_rating) as avg_rating,
    sum(total_sales) as total_sales,
    (sum(total_sales) * 100.0 / sum(sum(total_sales)) OVER (PARTITION BY category_name)) as market_share_percent
FROM products 
GROUP BY category_name, seller_name
ORDER BY category_name, market_share_percent DESC;
```

### Price Competitiveness Analysis
```sql
SELECT 
    seller_name,
    category_name,
    avg(price) as avg_price,
    avg(average_rating) as avg_rating,
    count() as product_count,
    -- Calculate price competitiveness score
    (avg(average_rating) * 0.6 + (100 - avg(price)) * 0.4) as competitiveness_score
FROM products 
GROUP BY seller_name, category_name
HAVING product_count >= 5
ORDER BY competitiveness_score DESC
LIMIT 30;
```

### Seller Market Position
```sql
SELECT 
    seller_name,
    count() as total_products,
    count(DISTINCT category_name) as categories_covered,
    avg(seller_rating) as avg_seller_rating,
    sum(total_sales) as total_sales,
    avg(price) as avg_price,
    avg(average_rating) as avg_product_rating
FROM products 
GROUP BY seller_name
HAVING total_products >= 20
ORDER BY total_sales DESC
LIMIT 20;
```

## Python Analytics Examples

### Market Overview Analysis
```python
import asyncio
from aliai.analytics import AnalyticsEngine

async def market_overview():
    analytics = AnalyticsEngine()
    
    # Get comprehensive market overview
    overview = await analytics.get_market_overview()
    
    print("=== MARKET OVERVIEW ===")
    print(f"Total Products: {overview['overview']['total_products']}")
    print(f"Total Categories: {overview['overview']['total_categories']}")
    print(f"Total Sellers: {overview['overview']['total_sellers']}")
    print(f"Average Price: ${overview['overview']['avg_price']:.2f}")
    print(f"Average Rating: {overview['overview']['avg_rating']:.2f}")
    
    print("\n=== TOP CATEGORIES ===")
    for i, category in enumerate(overview['top_categories'][:5], 1):
        print(f"{i}. {category['category_name']} - {category['product_count']} products")
    
    print("\n=== TOP SELLERS ===")
    for i, seller in enumerate(overview['top_sellers'][:5], 1):
        print(f"{i}. {seller['seller_name']} - {seller['total_sales']} total sales")
    
    analytics.close()

# Run the analysis
asyncio.run(market_overview())
```

### High-Margin Opportunity Detection
```python
import asyncio
from aliai.analytics import AnalyticsEngine

async def find_opportunities():
    analytics = AnalyticsEngine()
    
    # Find high-margin opportunities
    opportunities = await analytics.detect_high_margin_opportunities(
        min_rating=4.0,
        max_price=100.0
    )
    
    print("=== HIGH-MARGIN OPPORTUNITIES ===")
    for i, opp in enumerate(opportunities[:10], 1):
        print(f"{i}. {opp['title'][:60]}...")
        print(f"   Price: ${opp['price']:.2f}")
        print(f"   Rating: {opp['average_rating']:.1f}★ ({opp['total_reviews']} reviews)")
        print(f"   Sales: {opp['total_sales']}")
        print(f"   Margin Score: {opp['margin_potential_score']:.2f}")
        print(f"   Seller: {opp['seller_name']}")
        print()
    
    analytics.close()

# Run the analysis
asyncio.run(find_opportunities())
```

### Seasonal Trend Analysis
```python
import asyncio
from aliai.analytics import AnalyticsEngine

async def seasonal_analysis():
    analytics = AnalyticsEngine()
    
    # Analyze seasonal trends
    seasonal_data = await analytics.analyze_seasonal_trends(months=12)
    
    print("=== SEASONAL TREND ANALYSIS ===")
    for season, data in seasonal_data['seasonal_data'].items():
        print(f"\n{season.upper()} SEASON:")
        
        # Find peak month
        peak_month = max(data.keys(), key=lambda m: data[m]['total_sales'])
        peak_data = data[peak_month]
        
        print(f"  Peak Month: {peak_month}")
        print(f"  Products: {peak_data['product_count']}")
        print(f"  Total Sales: {peak_data['total_sales']}")
        print(f"  Avg Price: ${peak_data['avg_price']:.2f}")
        
        # Top categories for this season
        top_categories = sorted(
            peak_data['categories'].items(),
            key=lambda x: x[1]['sales'],
            reverse=True
        )[:3]
        
        print(f"  Top Categories:")
        for cat, stats in top_categories:
            print(f"    - {cat}: {stats['count']} products, {stats['sales']} sales")
    
    analytics.close()

# Run the analysis
asyncio.run(seasonal_analysis())
```

### Price Trend Analysis
```python
import asyncio
from aliai.analytics import AnalyticsEngine

async def price_analysis():
    analytics = AnalyticsEngine()
    
    # Analyze price trends
    price_trends = await analytics.analyze_price_trends(days=30)
    
    print("=== PRICE TREND ANALYSIS ===")
    overall_stats = price_trends['overall_stats']
    print(f"Analysis Period: {overall_stats['analysis_period_days']} days")
    print(f"Products Tracked: {overall_stats['total_products_tracked']}")
    print(f"Average Price: ${overall_stats['avg_price']:.2f}")
    print(f"Median Price: ${overall_stats['median_price']:.2f}")
    print(f"Price Range: ${overall_stats['price_range']:.2f}")
    
    print("\n=== TOP PRICE MOVERS ===")
    # Sort by absolute price change
    sorted_trends = sorted(
        price_trends['product_trends'].items(),
        key=lambda x: abs(x[1]['price_change_percent']),
        reverse=True
    )
    
    for product_id, trend in sorted_trends[:10]:
        print(f"Product: {product_id}")
        print(f"  Price Change: {trend['price_change_percent']:+.1f}%")
        print(f"  Initial: ${trend['initial_price']:.2f}")
        print(f"  Final: ${trend['final_price']:.2f}")
        print(f"  Volatility: {trend['price_volatility']:.2f}")
        print(f"  Category: {trend['category']}")
        print()
    
    analytics.close()

# Run the analysis
asyncio.run(price_analysis())
```

### Competitor Analysis
```python
import asyncio
from aliai.analytics import AnalyticsEngine

async def competitor_analysis():
    analytics = AnalyticsEngine()
    
    # Analyze competitors in electronics category
    competitors = await analytics.get_competitor_analysis(
        category_id="electronics",
        limit=20
    )
    
    print("=== COMPETITOR ANALYSIS ===")
    print(f"Category: {competitors['category_id']}")
    print(f"Total Competitors: {competitors['total_competitors']}")
    print(f"Total Market Sales: {competitors['total_market_sales']}")
    
    print("\n=== TOP COMPETITORS ===")
    for i, comp in enumerate(competitors['competitors'][:10], 1):
        print(f"{i}. {comp['seller_name']}")
        print(f"   Products: {comp['product_count']}")
        print(f"   Market Share: {comp['market_share']:.1f}%")
        print(f"   Total Sales: {comp['total_sales']}")
        print(f"   Avg Price: ${comp['avg_price']:.2f}")
        print(f"   Avg Rating: {comp['avg_rating']:.1f}★")
        print(f"   Seller Rating: {comp['seller_rating']:.1f}★")
        print()
    
    analytics.close()

# Run the analysis
asyncio.run(competitor_analysis())
```

## Usage Examples

### Running the Complete Pipeline
```bash
# Run full scraping and analysis pipeline
python main.py --mode full --verbose

# Scrape specific categories
python main.py --mode scrape --categories "https://www.aliexpress.com/category/100003070/electronics.html"

# Scrape search terms
python main.py --mode scrape --search "wireless headphones" "phone case" --pages 3

# Generate insights only
python main.py --mode insights

# Analyze existing data
python main.py --mode analyze
```

### Using Airflow DAGs
```bash
# Start Airflow webserver
airflow webserver --port 8080

# Start Airflow scheduler
airflow scheduler

# Trigger a DAG manually
airflow dags trigger aliexpress_daily_scraping

# Check DAG status
airflow dags list
```

### Database Operations
```python
from aliai.database import ClickHouseClient

# Connect to database
db = ClickHouseClient()

# Get product statistics
stats = await db.get_product_stats()
print(f"Total products: {stats['total_products']}")

# Get trending products
trending = await db.get_trending_products(days=7, limit=20)
for product in trending:
    print(f"{product['title']} - Score: {product['trend_score']}")

# Close connection
db.close()
```

This comprehensive set of queries and examples provides everything needed to analyze AliExpress data for business intelligence, trend detection, and dropshipping opportunities.
