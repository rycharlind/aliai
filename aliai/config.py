"""
AliAI - Core Configuration Module
Handles environment variables and application settings
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    host: str = Field(default="localhost", env="CLICKHOUSE_HOST")
    port: int = Field(default=9000, env="CLICKHOUSE_PORT")
    user: str = Field(default="default", env="CLICKHOUSE_USER")
    password: str = Field(default="", env="CLICKHOUSE_PASSWORD")
    database: str = Field(default="aliexpress", env="CLICKHOUSE_DATABASE")
    
    class Config:
        env_prefix = "CLICKHOUSE_"


class RedisConfig(BaseSettings):
    """Redis configuration settings"""
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    
    class Config:
        env_prefix = "REDIS_"


class ScrapingConfig(BaseSettings):
    """Scraping configuration settings"""
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_delay: float = Field(default=1.0, env="REQUEST_DELAY")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    timeout: int = Field(default=30, env="TIMEOUT")
    user_agent_rotation: bool = Field(default=True, env="USER_AGENT_ROTATION")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    rate_limit_per_day: int = Field(default=10000, env="RATE_LIMIT_PER_DAY")


class ProxyConfig(BaseSettings):
    """Proxy configuration settings"""
    enabled: bool = Field(default=False, env="PROXY_ENABLED")
    proxy_list: List[str] = Field(default_factory=list)
    rotation: bool = Field(default=True, env="PROXY_ROTATION")
    timeout: int = Field(default=10, env="PROXY_TIMEOUT")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.proxy_list_str := os.getenv("PROXY_LIST"):
            self.proxy_list = [p.strip() for p in self.proxy_list_str.split(",") if p.strip()]


class AIConfig(BaseSettings):
    """AI services configuration"""
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    sentiment_model: str = Field(default="text-davinci-003", env="SENTIMENT_MODEL")
    translation_enabled: bool = Field(default=True, env="TRANSLATION_ENABLED")
    mock_responses: bool = Field(default=False, env="MOCK_AI_RESPONSES")


class MonitoringConfig(BaseSettings):
    """Monitoring and logging configuration"""
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")


class AppConfig(BaseSettings):
    """Main application configuration"""
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")
    batch_size: int = Field(default=1000, env="BATCH_SIZE")
    processing_threads: int = Field(default=4, env="PROCESSING_THREADS")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    scraping: ScrapingConfig = ScrapingConfig()
    proxy: ProxyConfig = ProxyConfig()
    ai: AIConfig = AIConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get the global configuration instance"""
    return config


def reload_config():
    """Reload configuration from environment variables"""
    global config
    config = AppConfig()
    return config
