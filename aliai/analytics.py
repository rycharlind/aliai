"""
AliAI - Analytics Engine
Handles data analysis, trend detection, and business insights
"""

import asyncio
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
from aliai.database import ClickHouseClient
from aliai.ai_processor import AIProcessor


class AnalyticsEngine:
    """Main analytics engine for business insights"""
    
    def __init__(self):
        self.db = ClickHouseClient()
        self.ai_processor = AIProcessor()
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get comprehensive market overview"""
        try:
            # Get basic statistics
            stats = await self.db.get_product_stats()
            
            # Get top categories
            top_categories = await self.db.get_top_categories(10)
            
            # Get top sellers
            top_sellers = await self.db.get_top_sellers(10)
            
            # Get price distribution
            price_dist = await self.db.get_price_distribution()
            
            # Get trending products
            trending = await self.get_trending_products(days=7)
            
            return {
                'overview': stats,
                'top_categories': top_categories,
                'top_sellers': top_sellers,
                'price_distribution': price_dist,
                'trending_products': trending,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate market overview: {e}")
            return {}
    
    async def analyze_seasonal_trends(self, months: int = 12) -> Dict[str, Any]:
        """Analyze seasonal trends and patterns"""
        try:
            # Get products with seasonal tags
            query = """
            SELECT 
                seasonal_tags,
                category_name,
                count() as product_count,
                avg(price) as avg_price,
                sum(total_sales) as total_sales,
                toMonth(scraped_at) as month
            FROM products 
            WHERE seasonal_tags != []
            GROUP BY seasonal_tags, category_name, month
            ORDER BY month, total_sales DESC
            """
            
            result = self.db.client.execute(query)
            
            # Process seasonal data
            seasonal_data = {}
            for row in result:
                tags = row[0]
                category = row[1]
                count = row[2]
                price = float(row[3]) if row[3] else 0
                sales = row[4]
                month = row[5]
                
                for tag in tags:
                    if tag not in seasonal_data:
                        seasonal_data[tag] = {}
                    
                    if month not in seasonal_data[tag]:
                        seasonal_data[tag][month] = {
                            'product_count': 0,
                            'total_sales': 0,
                            'avg_price': 0,
                            'categories': {}
                        }
                    
                    seasonal_data[tag][month]['product_count'] += count
                    seasonal_data[tag][month]['total_sales'] += sales
                    seasonal_data[tag][month]['avg_price'] = price
                    seasonal_data[tag][month]['categories'][category] = {
                        'count': count,
                        'sales': sales,
                        'price': price
                    }
            
            return {
                'seasonal_data': seasonal_data,
                'analysis_period_months': months,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze seasonal trends: {e}")
            return {}
    
    async def detect_high_margin_opportunities(self, min_rating: float = 4.0, max_price: float = 100.0) -> List[Dict]:
        """Detect potential high-margin dropshipping opportunities"""
        try:
            query = f"""
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
                shipping_cost,
                free_shipping
            FROM products 
            WHERE average_rating >= {min_rating}
            AND price <= {max_price}
            AND total_reviews >= 10
            AND total_sales > 0
            ORDER BY (average_rating * total_sales) DESC
            LIMIT 100
            """
            
            result = self.db.client.execute(query)
            
            opportunities = []
            for row in result:
                # Calculate margin potential score
                margin_score = self._calculate_margin_potential(row)
                
                opportunities.append({
                    'product_id': row[0],
                    'title': row[1],
                    'price': float(row[2]) if row[2] else 0,
                    'original_price': float(row[3]) if row[3] else 0,
                    'discount_percentage': row[4],
                    'average_rating': float(row[5]) if row[5] else 0,
                    'total_reviews': row[6],
                    'total_sales': row[7],
                    'seller_name': row[8],
                    'category_name': row[9],
                    'shipping_cost': float(row[10]) if row[10] else 0,
                    'free_shipping': bool(row[11]),
                    'margin_potential_score': margin_score
                })
            
            # Sort by margin potential
            opportunities.sort(key=lambda x: x['margin_potential_score'], reverse=True)
            
            return opportunities[:50]  # Return top 50 opportunities
            
        except Exception as e:
            logger.error(f"Failed to detect high margin opportunities: {e}")
            return []
    
    def _calculate_margin_potential(self, product_row: Tuple) -> float:
        """Calculate margin potential score for a product"""
        try:
            price = float(product_row[2]) if product_row[2] else 0
            rating = float(product_row[5]) if product_row[5] else 0
            reviews = product_row[6]
            sales = product_row[7]
            
            if price == 0 or rating == 0:
                return 0.0
            
            # Base score from rating and sales volume
            volume_score = min(sales / 1000, 10)  # Normalize sales volume
            rating_score = rating * 2  # Scale rating to 0-10
            
            # Price competitiveness (lower price = higher margin potential)
            price_score = max(0, 10 - (price / 10))  # Lower price = higher score
            
            # Review credibility
            review_score = min(reviews / 100, 5)  # More reviews = higher credibility
            
            # Combined score
            margin_score = (volume_score * 0.3 + rating_score * 0.3 + 
                          price_score * 0.2 + review_score * 0.2)
            
            return round(margin_score, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate margin potential: {e}")
            return 0.0
    
    async def analyze_price_trends(self, category_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Analyze price trends for products or categories"""
        try:
            base_query = """
            SELECT 
                product_id,
                price,
                original_price,
                discount_percentage,
                scraped_at,
                category_name
            FROM products 
            WHERE scraped_at >= now() - INTERVAL {days} DAY
            """.format(days=days)
            
            if category_id:
                base_query += f" AND category_id = '{category_id}'"
            
            base_query += " ORDER BY product_id, scraped_at"
            
            result = self.db.client.execute(base_query)
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(result, columns=[
                'product_id', 'price', 'original_price', 'discount_percentage',
                'scraped_at', 'category_name'
            ])
            
            if df.empty:
                return {}
            
            # Analyze price trends
            price_analysis = {}
            
            for product_id, group in df.groupby('product_id'):
                if len(group) < 2:
                    continue
                
                prices = group['price'].values
                dates = pd.to_datetime(group['scraped_at'])
                
                # Calculate price change
                price_change = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
                
                # Calculate volatility
                price_volatility = np.std(prices) / np.mean(prices) if len(prices) > 1 else 0
                
                price_analysis[product_id] = {
                    'initial_price': float(prices[0]),
                    'final_price': float(prices[-1]),
                    'price_change_percent': float(price_change * 100),
                    'price_volatility': float(price_volatility),
                    'data_points': len(prices),
                    'category': group['category_name'].iloc[0]
                }
            
            # Overall statistics
            all_prices = df['price'].values
            overall_stats = {
                'avg_price': float(np.mean(all_prices)),
                'median_price': float(np.median(all_prices)),
                'price_range': float(np.max(all_prices) - np.min(all_prices)),
                'total_products_tracked': len(price_analysis),
                'analysis_period_days': days
            }
            
            return {
                'overall_stats': overall_stats,
                'product_trends': price_analysis,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze price trends: {e}")
            return {}
    
    async def get_competitor_analysis(self, category_id: str, limit: int = 20) -> Dict[str, Any]:
        """Analyze competitors in a specific category"""
        try:
            query = f"""
            SELECT 
                seller_id,
                seller_name,
                count() as product_count,
                avg(price) as avg_price,
                avg(average_rating) as avg_rating,
                sum(total_sales) as total_sales,
                avg(seller_rating) as seller_rating,
                count(DISTINCT category_id) as categories_count
            FROM products 
            WHERE category_id = '{category_id}'
            GROUP BY seller_id, seller_name
            ORDER BY total_sales DESC
            LIMIT {limit}
            """
            
            result = self.db.client.execute(query)
            
            competitors = []
            for row in result:
                competitors.append({
                    'seller_id': row[0],
                    'seller_name': row[1],
                    'product_count': row[2],
                    'avg_price': float(row[3]) if row[3] else 0,
                    'avg_rating': float(row[4]) if row[4] else 0,
                    'total_sales': row[5],
                    'seller_rating': float(row[6]) if row[6] else 0,
                    'categories_count': row[7],
                    'market_share': 0  # Will be calculated below
                })
            
            # Calculate market share
            total_sales = sum(comp['total_sales'] for comp in competitors)
            for comp in competitors:
                comp['market_share'] = (comp['total_sales'] / total_sales * 100) if total_sales > 0 else 0
            
            return {
                'category_id': category_id,
                'competitors': competitors,
                'total_competitors': len(competitors),
                'total_market_sales': total_sales,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze competitors: {e}")
            return {}
    
    async def get_trending_products(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """Get trending products based on multiple factors"""
        try:
            # Get products with high activity in recent days
            query = f"""
            SELECT 
                product_id,
                title,
                price,
                average_rating,
                total_reviews,
                total_sales,
                category_name,
                seller_name,
                scraped_at,
                trend_score
            FROM products 
            WHERE scraped_at >= now() - INTERVAL {days} DAY
            AND average_rating >= 4.0
            AND total_reviews >= 5
            ORDER BY 
                (total_sales * average_rating) DESC,
                total_reviews DESC,
                trend_score DESC
            LIMIT {limit}
            """
            
            result = self.db.client.execute(query)
            
            trending = []
            for row in result:
                trending.append({
                    'product_id': row[0],
                    'title': row[1],
                    'price': float(row[2]) if row[2] else 0,
                    'average_rating': float(row[3]) if row[3] else 0,
                    'total_reviews': row[4],
                    'total_sales': row[5],
                    'category_name': row[6],
                    'seller_name': row[7],
                    'scraped_at': row[8],
                    'trend_score': float(row[9]) if row[9] else 0,
                    'trend_rank': len(trending) + 1
                })
            
            return trending
            
        except Exception as e:
            logger.error(f"Failed to get trending products: {e}")
            return []
    
    async def generate_business_report(self) -> Dict[str, Any]:
        """Generate comprehensive business intelligence report"""
        try:
            logger.info("Generating comprehensive business report...")
            
            # Market overview
            market_overview = await self.get_market_overview()
            
            # Seasonal trends
            seasonal_trends = await self.analyze_seasonal_trends()
            
            # High margin opportunities
            margin_opportunities = await self.detect_high_margin_opportunities()
            
            # Price trends
            price_trends = await self.analyze_price_trends()
            
            # Top categories analysis
            top_categories = await self.db.get_top_categories(10)
            
            # Top sellers analysis
            top_sellers = await self.db.get_top_sellers(10)
            
            report = {
                'report_metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'report_type': 'comprehensive_business_intelligence',
                    'data_sources': ['aliexpress_scraping', 'ai_analysis', 'trend_detection']
                },
                'executive_summary': {
                    'total_products_analyzed': market_overview.get('overview', {}).get('total_products', 0),
                    'total_categories': market_overview.get('overview', {}).get('total_categories', 0),
                    'total_sellers': market_overview.get('overview', {}).get('total_sellers', 0),
                    'avg_market_price': market_overview.get('overview', {}).get('avg_price', 0),
                    'avg_market_rating': market_overview.get('overview', {}).get('avg_rating', 0)
                },
                'market_overview': market_overview,
                'seasonal_analysis': seasonal_trends,
                'opportunities': {
                    'high_margin_products': margin_opportunities[:20],
                    'trending_products': await self.get_trending_products(days=7, limit=20)
                },
                'competitive_landscape': {
                    'top_categories': top_categories,
                    'top_sellers': top_sellers,
                    'price_distribution': market_overview.get('price_distribution', {})
                },
                'price_analysis': price_trends,
                'recommendations': await self._generate_recommendations(market_overview, margin_opportunities)
            }
            
            logger.info("Business report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate business report: {e}")
            return {}
    
    async def _generate_recommendations(self, market_overview: Dict, opportunities: List[Dict]) -> List[str]:
        """Generate business recommendations based on analysis"""
        recommendations = []
        
        try:
            # Analyze top categories
            top_categories = market_overview.get('top_categories', [])
            if top_categories:
                top_category = top_categories[0]
                recommendations.append(
                    f"Focus on {top_category['category_name']} category - "
                    f"highest product count ({top_category['product_count']}) with "
                    f"average price ${top_category['avg_price']:.2f}"
                )
            
            # Analyze high-margin opportunities
            if opportunities:
                top_opportunity = opportunities[0]
                recommendations.append(
                    f"Consider dropshipping {top_opportunity['title'][:50]}... - "
                    f"high margin potential (score: {top_opportunity['margin_potential_score']}) "
                    f"with {top_opportunity['average_rating']:.1f}★ rating"
                )
            
            # Analyze price distribution
            price_dist = market_overview.get('price_distribution', {})
            if price_dist:
                median_price = price_dist.get('median', 0)
                recommendations.append(
                    f"Target products around ${median_price:.2f} median price point "
                    f"for optimal market positioning"
                )
            
            # Analyze seasonal trends
            recommendations.append(
                "Monitor seasonal trends and prepare inventory for upcoming "
                "holiday seasons (Halloween, Christmas, Summer)"
            )
            
            # General recommendations
            recommendations.extend([
                "Focus on products with 4+ star ratings and 10+ reviews for credibility",
                "Consider free shipping offers to increase conversion rates",
                "Monitor competitor pricing weekly to maintain competitive advantage",
                "Use AI sentiment analysis to identify product improvement opportunities"
            ])
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations.append("Unable to generate specific recommendations at this time")
        
        return recommendations
    
    def close(self):
        """Close database connection"""
        self.db.close()


# Example usage
async def main():
    """Example usage of analytics engine"""
    analytics = AnalyticsEngine()
    
    # Generate comprehensive report
    report = await analytics.generate_business_report()
    
    print("=== BUSINESS INTELLIGENCE REPORT ===")
    print(f"Total Products: {report.get('executive_summary', {}).get('total_products_analyzed', 0)}")
    print(f"Total Categories: {report.get('executive_summary', {}).get('total_categories', 0)}")
    
    # Show top opportunities
    opportunities = report.get('opportunities', {}).get('high_margin_products', [])
    print(f"\nTop High-Margin Opportunities:")
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"{i}. {opp['title'][:50]}... - Score: {opp['margin_potential_score']}")
    
    # Show recommendations
    recommendations = report.get('recommendations', [])
    print(f"\nRecommendations:")
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"{i}. {rec}")
    
    analytics.close()


if __name__ == "__main__":
    asyncio.run(main())
