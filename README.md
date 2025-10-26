# AliAI - AliExpress Scraping & Analysis System

A scalable, AI-powered system for scraping AliExpress product data and performing large-scale analysis using ClickHouse.

## Features

- **Automated Scraping**: Respectful web scraping with rate limiting and proxy support
- **AI-Powered Analysis**: Sentiment analysis, product categorization, and trend detection
- **Scalable Storage**: ClickHouse database optimized for analytical queries
- **Real-time Monitoring**: Health checks, error tracking, and performance metrics
- **Automated Scheduling**: Airflow-based workflow orchestration

## Quick Start

### Prerequisites

- Python 3.9+
- ClickHouse server
- Redis (for task queue)
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd aliai

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize ClickHouse schema
python scripts/init_database.py

# Start the scraping service
python main.py
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Scraping
MAX_CONCURRENT_REQUESTS=10
REQUEST_DELAY=1.0
PROXY_LIST=proxy1:port,proxy2:port

# AI Services
OPENAI_API_KEY=your_openai_key
SENTIMENT_MODEL=text-davinci-003

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

## Get Airflow UI username/password
`docker compose logs airflow-webserver | grep "Password for user 'admin'"`

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## Usage

### Basic Scraping

```python
from aliai.scraper import AliExpressScraper

scraper = AliExpressScraper()
products = scraper.scrape_category("Electronics", max_pages=10)
```

### AI Analysis

```python
from aliai.ai_processor import AIProcessor

processor = AIProcessor()
sentiment = processor.analyze_sentiment("Great product, fast shipping!")
```

### Data Analysis

```python
from aliai.analytics import AnalyticsEngine

analytics = AnalyticsEngine()
trends = analytics.detect_trends(days=30)
```

## Database Schema

See [schema/clickhouse_schema.sql](schema/clickhouse_schema.sql) for the complete database schema.

## Monitoring

Access monitoring dashboards:
- Grafana: http://localhost:3000
- Airflow: http://localhost:8080

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.