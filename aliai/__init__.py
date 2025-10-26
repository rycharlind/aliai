"""
AliAI - Package Initialization
"""

__version__ = "1.0.0"
__author__ = "AliAI Team"
__description__ = "AI-powered AliExpress scraping and analysis system"

from .config import get_config, AppConfig
from .scraper import AliExpressScraper, ProductData
from .ai_processor import AIProcessor, SentimentAnalyzer, ProductCategorizer, TrendDetector
from .database import ClickHouseClient
from .analytics import AnalyticsEngine

__all__ = [
    'get_config',
    'AppConfig', 
    'AliExpressScraper',
    'ProductData',
    'AIProcessor',
    'SentimentAnalyzer',
    'ProductCategorizer', 
    'TrendDetector',
    'ClickHouseClient',
    'AnalyticsEngine'
]
