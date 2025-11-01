"""
AliAI - Core Configuration Module
Handles environment variables and application settings
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database configuration settings"""
    model_config = SettingsConfigDict(env_prefix="CLICKHOUSE_")
    
    host: str = Field(default="localhost")
    port: int = Field(default=9000)
    user: str = Field(default="default")
    password: str = Field(default="")
    database: str = Field(default="aliexpress")


class RedisConfig(BaseSettings):
    """Redis configuration settings"""
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    password: Optional[str] = Field(default=None)
    db: int = Field(default=0)


class ScrapingConfig(BaseSettings):
    """Scraping configuration settings"""
    model_config = SettingsConfigDict(extra='ignore')
    
    max_concurrent_requests: int = Field(default=10)
    request_delay: float = Field(default=1.0)
    max_retries: int = Field(default=3)
    timeout: int = Field(default=30)
    user_agent_rotation: bool = Field(default=True)
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_per_hour: int = Field(default=1000)
    rate_limit_per_day: int = Field(default=10000)


class ProxyConfig(BaseSettings):
    """Proxy configuration settings"""
    model_config = SettingsConfigDict(extra='ignore')
    
    enabled: bool = Field(default=False)
    proxy_list: str = Field(default="")
    rotation: bool = Field(default=True)
    timeout: int = Field(default=10)
    
    @property
    def proxy_list_parsed(self) -> List[str]:
        """Parse proxy list from comma-separated string"""
        if not self.proxy_list:
            return []
        return [p.strip() for p in self.proxy_list.split(",") if p.strip()]


class AIConfig(BaseSettings):
    """AI services configuration"""
    model_config = SettingsConfigDict(extra='ignore')
    
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-3.5-turbo")
    sentiment_model: str = Field(default="text-davinci-003")
    translation_enabled: bool = Field(default=True)
    mock_responses: bool = Field(default=False)


class MonitoringConfig(BaseSettings):
    """Monitoring and logging configuration"""
    model_config = SettingsConfigDict(extra='ignore')
    
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    metrics_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)


class AppConfig(BaseSettings):
    """Main application configuration"""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra='ignore')
    
    debug: bool = Field(default=False)
    testing: bool = Field(default=False)
    batch_size: int = Field(default=1000)
    processing_threads: int = Field(default=4)
    cache_ttl: int = Field(default=3600)
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    scraping: ScrapingConfig = ScrapingConfig()
    proxy: ProxyConfig = ProxyConfig()
    ai: AIConfig = AIConfig()
    monitoring: MonitoringConfig = MonitoringConfig()


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
