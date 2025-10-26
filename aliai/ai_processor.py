"""
AliAI - AI Processing Module
Handles sentiment analysis, product categorization, and trend detection
"""

import asyncio
import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import openai
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import pandas as pd
import numpy as np
from loguru import logger
from aliai.config import get_config


@dataclass
class SentimentResult:
    """Result of sentiment analysis"""
    text: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str    # 'positive', 'negative', 'neutral'
    confidence: float
    key_phrases: List[str]
    language: str


@dataclass
class ProductCategory:
    """Product categorization result"""
    category_id: str
    category_name: str
    confidence: float
    subcategories: List[str]
    seasonal_tags: List[str]


@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    product_id: str
    trend_type: str  # 'seasonal', 'viral', 'price_drop', 'new_arrival'
    trend_score: float
    trend_direction: str  # 'up', 'down', 'stable'
    confidence: float
    duration_days: int
    peak_score: float


class SentimentAnalyzer:
    """Handles sentiment analysis of reviews and text"""
    
    def __init__(self):
        self.config = get_config()
        self.openai_client = None
        self.local_model = None
        
        # Initialize OpenAI client if API key is provided
        if self.config.ai.openai_api_key:
            openai.api_key = self.config.ai.openai_api_key
            self.openai_client = openai
        
        # Initialize local model as fallback
        try:
            self.local_model = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True
            )
        except Exception as e:
            logger.warning(f"Failed to load local sentiment model: {e}")
    
    async def analyze_sentiment(self, text: str, use_openai: bool = True) -> SentimentResult:
        """Analyze sentiment of text"""
        if not text or not text.strip():
            return SentimentResult(
                text=text,
                sentiment_score=0.0,
                sentiment_label='neutral',
                confidence=0.0,
                key_phrases=[],
                language='en'
            )
        
        # Detect language
        language = self._detect_language(text)
        
        # Translate if needed
        translated_text = text
        if language != 'en' and self.config.ai.translation_enabled:
            translated_text = await self._translate_text(text, target_language='en')
        
        # Analyze sentiment
        if use_openai and self.openai_client and not self.config.ai.mock_responses:
            sentiment_result = await self._analyze_with_openai(translated_text)
        else:
            sentiment_result = await self._analyze_with_local_model(translated_text)
        
        # Extract key phrases
        key_phrases = await self._extract_key_phrases(translated_text)
        
        return SentimentResult(
            text=text,
            sentiment_score=sentiment_result['score'],
            sentiment_label=sentiment_result['label'],
            confidence=sentiment_result['confidence'],
            key_phrases=key_phrases,
            language=language
        )
    
    async def _analyze_with_openai(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using OpenAI API"""
        try:
            prompt = f"""
            Analyze the sentiment of the following product review text and provide:
            1. Sentiment score (-1 to 1, where -1 is very negative, 0 is neutral, 1 is very positive)
            2. Sentiment label (positive, negative, or neutral)
            3. Confidence score (0 to 1)
            
            Text: "{text}"
            
            Respond in JSON format:
            {{
                "sentiment_score": <float>,
                "sentiment_label": "<string>",
                "confidence": <float>
            }}
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model=self.config.ai.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            result = response.choices[0].message.content
            # Parse JSON response
            import json
            return json.loads(result)
            
        except Exception as e:
            logger.error(f"OpenAI sentiment analysis failed: {e}")
            return await self._analyze_with_local_model(text)
    
    async def _analyze_with_local_model(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using local model"""
        try:
            if not self.local_model:
                return {
                    'score': 0.0,
                    'label': 'neutral',
                    'confidence': 0.0
                }
            
            # Truncate text if too long
            if len(text) > 512:
                text = text[:512]
            
            results = self.local_model(text)
            
            # Find the highest confidence result
            best_result = max(results[0], key=lambda x: x['score'])
            
            # Convert to our format
            label_map = {
                'LABEL_0': 'negative',
                'LABEL_1': 'neutral', 
                'LABEL_2': 'positive'
            }
            
            sentiment_map = {
                'negative': -0.5,
                'neutral': 0.0,
                'positive': 0.5
            }
            
            label = label_map.get(best_result['label'], 'neutral')
            score = sentiment_map.get(label, 0.0)
            
            return {
                'score': score,
                'label': label,
                'confidence': best_result['score']
            }
            
        except Exception as e:
            logger.error(f"Local sentiment analysis failed: {e}")
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0
            }
    
    async def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text"""
        try:
            if self.openai_client and not self.config.ai.mock_responses:
                prompt = f"""
                Extract the 5 most important key phrases from this product review text.
                Focus on product features, quality, shipping, customer service, etc.
                
                Text: "{text}"
                
                Respond with a JSON array of strings:
                ["phrase1", "phrase2", "phrase3", "phrase4", "phrase5"]
                """
                
                response = await self.openai_client.ChatCompletion.acreate(
                    model=self.config.ai.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=100
                )
                
                result = response.choices[0].message.content
                import json
                return json.loads(result)
            else:
                # Simple keyword extraction as fallback
                return self._extract_keywords_simple(text)
                
        except Exception as e:
            logger.error(f"Key phrase extraction failed: {e}")
            return self._extract_keywords_simple(text)
    
    def _extract_keywords_simple(self, text: str) -> List[str]:
        """Simple keyword extraction fallback"""
        # Common product-related keywords
        keywords = [
            'quality', 'shipping', 'fast', 'slow', 'good', 'bad', 'excellent',
            'terrible', 'recommend', 'worth', 'price', 'cheap', 'expensive',
            'durable', 'fragile', 'easy', 'difficult', 'customer service'
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:5]
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection"""
        # This is a simplified version - in production, use a proper language detection library
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars > len(text) * 0.3:
            return 'zh'
        
        # Check for common non-English patterns
        if re.search(r'[а-яё]', text.lower()):
            return 'ru'
        if re.search(r'[áéíóúñ]', text.lower()):
            return 'es'
        if re.search(r'[àâäéèêëïîôöùûüÿç]', text.lower()):
            return 'fr'
        
        return 'en'
    
    async def _translate_text(self, text: str, target_language: str = 'en') -> str:
        """Translate text to target language"""
        if not self.openai_client or self.config.ai.mock_responses:
            return text
        
        try:
            prompt = f"Translate the following text to {target_language}: {text}"
            
            response = await self.openai_client.ChatCompletion.acreate(
                model=self.config.ai.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text


class ProductCategorizer:
    """Handles automatic product categorization"""
    
    def __init__(self):
        self.config = get_config()
        self.openai_client = None
        
        if self.config.ai.openai_api_key:
            openai.api_key = self.config.ai.openai_api_key
            self.openai_client = openai
        
        # Define category mappings
        self.category_mappings = {
            'electronics': ['phone', 'computer', 'electronic', 'tech', 'digital', 'wireless', 'bluetooth'],
            'clothing': ['shirt', 'dress', 'pants', 'shoes', 'jacket', 'fashion', 'wear'],
            'home': ['furniture', 'decoration', 'kitchen', 'bedroom', 'living', 'home'],
            'beauty': ['makeup', 'skincare', 'beauty', 'cosmetic', 'perfume', 'hair'],
            'sports': ['fitness', 'sport', 'exercise', 'gym', 'outdoor', 'athletic'],
            'automotive': ['car', 'auto', 'vehicle', 'motor', 'engine', 'automotive'],
            'toys': ['toy', 'game', 'children', 'kids', 'play', 'educational'],
            'jewelry': ['ring', 'necklace', 'bracelet', 'jewelry', 'gold', 'silver']
        }
        
        self.seasonal_keywords = {
            'halloween': ['halloween', 'spooky', 'costume', 'pumpkin', 'ghost', 'witch'],
            'christmas': ['christmas', 'holiday', 'gift', 'santa', 'tree', 'ornament'],
            'summer': ['summer', 'beach', 'swim', 'vacation', 'hot', 'sunny'],
            'winter': ['winter', 'cold', 'snow', 'warm', 'coat', 'heater'],
            'spring': ['spring', 'flower', 'garden', 'fresh', 'renewal'],
            'fall': ['fall', 'autumn', 'harvest', 'leaves', 'cozy']
        }
    
    async def categorize_product(self, title: str, description: str = "", tags: List[str] = None) -> ProductCategory:
        """Categorize a product based on title, description, and tags"""
        if tags is None:
            tags = []
        
        # Combine all text for analysis
        full_text = f"{title} {description} {' '.join(tags)}".lower()
        
        # Find best category match
        best_category = None
        best_score = 0.0
        
        for category, keywords in self.category_mappings.items():
            score = sum(1 for keyword in keywords if keyword in full_text)
            if score > best_score:
                best_score = score
                best_category = category
        
        # Use AI for more sophisticated categorization if available
        if self.openai_client and not self.config.ai.mock_responses:
            ai_category = await self._categorize_with_ai(title, description, tags)
            if ai_category['confidence'] > 0.7:
                best_category = ai_category['category']
                best_score = ai_category['confidence']
        
        # Detect seasonal relevance
        seasonal_tags = self._detect_seasonal_tags(full_text)
        
        return ProductCategory(
            category_id=best_category or 'other',
            category_name=best_category or 'Other',
            confidence=min(best_score / 10.0, 1.0),  # Normalize score
            subcategories=[],
            seasonal_tags=seasonal_tags
        )
    
    async def _categorize_with_ai(self, title: str, description: str, tags: List[str]) -> Dict[str, Any]:
        """Use AI for product categorization"""
        try:
            prompt = f"""
            Categorize this product into one of these categories:
            electronics, clothing, home, beauty, sports, automotive, toys, jewelry, other
            
            Product Title: "{title}"
            Description: "{description}"
            Tags: {', '.join(tags)}
            
            Also identify any seasonal relevance (halloween, christmas, summer, winter, spring, fall, none).
            
            Respond in JSON format:
            {{
                "category": "<category_name>",
                "confidence": <float 0-1>,
                "seasonal_tags": ["tag1", "tag2"]
            }}
            """
            
            response = await self.openai_client.ChatCompletion.acreate(
                model=self.config.ai.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100
            )
            
            result = response.choices[0].message.content
            import json
            return json.loads(result)
            
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
            return {
                'category': 'other',
                'confidence': 0.0,
                'seasonal_tags': []
            }
    
    def _detect_seasonal_tags(self, text: str) -> List[str]:
        """Detect seasonal relevance in text"""
        seasonal_tags = []
        
        for season, keywords in self.seasonal_keywords.items():
            if any(keyword in text for keyword in keywords):
                seasonal_tags.append(season)
        
        return seasonal_tags


class TrendDetector:
    """Detects trending products and categories"""
    
    def __init__(self):
        self.config = get_config()
    
    async def detect_trends(self, products_data: List[Dict], days: int = 30) -> List[TrendAnalysis]:
        """Detect trending products from historical data"""
        trends = []
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(products_data)
        
        if df.empty:
            return trends
        
        # Group by product and analyze trends
        for product_id, group in df.groupby('product_id'):
            trend_analysis = await self._analyze_product_trend(product_id, group, days)
            if trend_analysis:
                trends.append(trend_analysis)
        
        return trends
    
    async def _analyze_product_trend(self, product_id: str, data: pd.DataFrame, days: int) -> Optional[TrendAnalysis]:
        """Analyze trend for a single product"""
        try:
            # Sort by date
            data = data.sort_values('scraped_at')
            
            if len(data) < 2:
                return None
            
            # Calculate trend metrics
            price_trend = self._calculate_price_trend(data)
            sales_trend = self._calculate_sales_trend(data)
            rating_trend = self._calculate_rating_trend(data)
            
            # Determine overall trend
            trend_score = (price_trend + sales_trend + rating_trend) / 3
            
            # Determine trend type
            trend_type = self._determine_trend_type(data, trend_score)
            
            # Determine direction
            trend_direction = 'up' if trend_score > 0.1 else 'down' if trend_score < -0.1 else 'stable'
            
            return TrendAnalysis(
                product_id=product_id,
                trend_type=trend_type,
                trend_score=trend_score,
                trend_direction=trend_direction,
                confidence=min(abs(trend_score) * 2, 1.0),
                duration_days=days,
                peak_score=trend_score
            )
            
        except Exception as e:
            logger.error(f"Trend analysis failed for product {product_id}: {e}")
            return None
    
    def _calculate_price_trend(self, data: pd.DataFrame) -> float:
        """Calculate price trend score"""
        if 'price' not in data.columns or len(data) < 2:
            return 0.0
        
        prices = data['price'].values
        if len(prices) < 2:
            return 0.0
        
        # Calculate price change percentage
        price_change = (prices[-1] - prices[0]) / prices[0]
        return -price_change  # Negative price change is positive trend
    
    def _calculate_sales_trend(self, data: pd.DataFrame) -> float:
        """Calculate sales trend score"""
        if 'total_sales' not in data.columns or len(data) < 2:
            return 0.0
        
        sales = data['total_sales'].values
        if len(sales) < 2:
            return 0.0
        
        # Calculate sales growth
        sales_growth = (sales[-1] - sales[0]) / max(sales[0], 1)
        return sales_growth
    
    def _calculate_rating_trend(self, data: pd.DataFrame) -> float:
        """Calculate rating trend score"""
        if 'average_rating' not in data.columns or len(data) < 2:
            return 0.0
        
        ratings = data['average_rating'].dropna().values
        if len(ratings) < 2:
            return 0.0
        
        # Calculate rating improvement
        rating_change = ratings[-1] - ratings[0]
        return rating_change / 5.0  # Normalize to 0-1 scale
    
    def _determine_trend_type(self, data: pd.DataFrame, trend_score: float) -> str:
        """Determine the type of trend"""
        if abs(trend_score) < 0.1:
            return 'stable'
        elif trend_score > 0.3:
            return 'viral'
        elif trend_score < -0.2:
            return 'price_drop'
        else:
            return 'seasonal'


class AIProcessor:
    """Main AI processing coordinator"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.product_categorizer = ProductCategorizer()
        self.trend_detector = TrendDetector()
    
    async def process_review(self, review_text: str) -> SentimentResult:
        """Process a single review"""
        return await self.sentiment_analyzer.analyze_sentiment(review_text)
    
    async def process_product(self, title: str, description: str = "", tags: List[str] = None) -> ProductCategory:
        """Process a single product for categorization"""
        return await self.product_categorizer.categorize_product(title, description, tags)
    
    async def process_trends(self, products_data: List[Dict], days: int = 30) -> List[TrendAnalysis]:
        """Process products for trend detection"""
        return await self.trend_detector.detect_trends(products_data, days)
    
    async def batch_process_reviews(self, reviews: List[str]) -> List[SentimentResult]:
        """Process multiple reviews in batch"""
        tasks = [self.process_review(review) for review in reviews]
        return await asyncio.gather(*tasks)
    
    async def batch_process_products(self, products: List[Dict]) -> List[ProductCategory]:
        """Process multiple products in batch"""
        tasks = []
        for product in products:
            task = self.process_product(
                product.get('title', ''),
                product.get('description', ''),
                product.get('tags', [])
            )
            tasks.append(task)
        return await asyncio.gather(*tasks)


# Example usage
async def main():
    """Example usage of AI processing"""
    processor = AIProcessor()
    
    # Process a review
    review = "Great product! Fast shipping and excellent quality. Highly recommended!"
    sentiment = await processor.process_review(review)
    print(f"Sentiment: {sentiment.sentiment_label} (score: {sentiment.sentiment_score})")
    
    # Process a product
    product = {
        'title': 'Wireless Bluetooth Headphones',
        'description': 'High-quality wireless headphones with noise cancellation',
        'tags': ['electronics', 'audio', 'wireless']
    }
    category = await processor.process_product(
        product['title'], 
        product['description'], 
        product['tags']
    )
    print(f"Category: {category.category_name} (confidence: {category.confidence})")


if __name__ == "__main__":
    asyncio.run(main())
