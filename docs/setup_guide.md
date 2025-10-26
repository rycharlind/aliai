# AliAI - Setup and Deployment Guide

This guide will help you set up and deploy the AliAI system for AliExpress scraping and analysis.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Configuration](#configuration)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **Python 3.9+**
- **ClickHouse Server** (for data storage)
- **Redis** (for task queue and caching)
- **PostgreSQL** (for Airflow metadata)
- **8GB+ RAM** (recommended for large-scale scraping)
- **50GB+ Storage** (for data and logs)

### External Services
- **OpenAI API Key** (for AI analysis)
- **Proxy Service** (optional, for large-scale scraping)

## Local Development Setup

### 1. Clone and Setup Project
```bash
# Clone the repository
git clone <repository-url>
cd aliai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install ClickHouse
```bash
# On macOS with Homebrew
brew install clickhouse

# On Ubuntu/Debian
sudo apt-get install clickhouse-server clickhouse-client

# Start ClickHouse
sudo systemctl start clickhouse-server
sudo systemctl enable clickhouse-server
```

### 3. Install Redis
```bash
# On macOS with Homebrew
brew install redis

# On Ubuntu/Debian
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 4. Install PostgreSQL (for Airflow)
```bash
# On macOS with Homebrew
brew install postgresql

# On Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 5. Configure Environment
```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

### 6. Initialize Database
```bash
# Create ClickHouse database and tables
python scripts/init_database.py

# Initialize Airflow database
airflow db init

# Create Airflow admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

### 7. Start Services
```bash
# Start Airflow webserver (in one terminal)
airflow webserver --port 8080

# Start Airflow scheduler (in another terminal)
airflow scheduler

# Test the scraper
python main.py --mode scrape --search "wireless headphones" --pages 1
```

## Docker Deployment

### 1. Docker Compose Setup
Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "9000:9000"
      - "8123:8123"
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./schema/clickhouse_schema.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      CLICKHOUSE_DB: aliexpress
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
    networks:
      - aliai-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - aliai-network

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: airflow
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aliai-network

  aliai-scraper:
    build: .
    depends_on:
      - clickhouse
      - redis
      - postgres
    environment:
      - CLICKHOUSE_HOST=clickhouse
      - REDIS_HOST=redis
      - AIRFLOW_DB_CONN=postgresql://airflow:airflow@postgres:5432/airflow
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - aliai-network
    command: python main.py --mode full

  airflow-webserver:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      - AIRFLOW_DB_CONN=postgresql://airflow:airflow@postgres:5432/airflow
      - AIRFLOW_EXECUTOR=LocalExecutor
    ports:
      - "8080:8080"
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./airflow/logs:/opt/airflow/logs
      - ./airflow/plugins:/opt/airflow/plugins
    networks:
      - aliai-network
    command: airflow webserver

  airflow-scheduler:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      - AIRFLOW_DB_CONN=postgresql://airflow:airflow@postgres:5432/airflow
      - AIRFLOW_EXECUTOR=LocalExecutor
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./airflow/logs:/opt/airflow/logs
      - ./airflow/plugins:/opt/airflow/plugins
    networks:
      - aliai-network
    command: airflow scheduler

volumes:
  clickhouse_data:
  redis_data:
  postgres_data:

networks:
  aliai-network:
    driver: bridge
```

### 2. Dockerfile
Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV AIRFLOW_HOME=/opt/airflow

# Expose ports
EXPOSE 8080 9090

# Default command
CMD ["python", "main.py", "--mode", "full"]
```

### 3. Deploy with Docker
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f aliai-scraper

# Stop services
docker-compose down
```

## Production Deployment

### 1. Kubernetes Deployment
Create `k8s/namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aliai
```

Create `k8s/clickhouse.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: clickhouse
  namespace: aliai
spec:
  replicas: 1
  selector:
    matchLabels:
      app: clickhouse
  template:
    metadata:
      labels:
        app: clickhouse
    spec:
      containers:
      - name: clickhouse
        image: clickhouse/clickhouse-server:latest
        ports:
        - containerPort: 9000
        - containerPort: 8123
        env:
        - name: CLICKHOUSE_DB
          value: "aliexpress"
        volumeMounts:
        - name: clickhouse-storage
          mountPath: /var/lib/clickhouse
      volumes:
      - name: clickhouse-storage
        persistentVolumeClaim:
          claimName: clickhouse-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: clickhouse-service
  namespace: aliai
spec:
  selector:
    app: clickhouse
  ports:
  - port: 9000
    targetPort: 9000
  - port: 8123
    targetPort: 8123
```

### 2. Helm Chart
Create `helm/aliai/Chart.yaml`:
```yaml
apiVersion: v2
name: aliai
description: AliExpress Scraping and Analysis System
type: application
version: 0.1.0
appVersion: "1.0.0"
```

### 3. Deploy to Production
```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy ClickHouse
kubectl apply -f k8s/clickhouse.yaml

# Deploy with Helm
helm install aliai ./helm/aliai

# Check deployment
kubectl get pods -n aliai
```

## Configuration

### Environment Variables
Key configuration options in `.env`:

```bash
# Database Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DATABASE=aliexpress

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Scraping Configuration
MAX_CONCURRENT_REQUESTS=10
REQUEST_DELAY=1.0
MAX_RETRIES=3
TIMEOUT=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_PER_DAY=10000

# AI Services
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
SENTIMENT_MODEL=text-davinci-003

# Proxy Configuration
PROXY_ENABLED=false
PROXY_LIST=proxy1:port,proxy2:port
PROXY_ROTATION=true

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=true
PROMETHEUS_PORT=9090
```

### Scraping Configuration
Adjust scraping parameters based on your needs:

```python
# Conservative scraping (respectful)
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY=2.0
RATE_LIMIT_PER_MINUTE=30

# Aggressive scraping (use with caution)
MAX_CONCURRENT_REQUESTS=20
REQUEST_DELAY=0.5
RATE_LIMIT_PER_MINUTE=120
```

## Monitoring and Maintenance

### 1. Health Checks
```bash
# Check database connection
python -c "from aliai.database import ClickHouseClient; db = ClickHouseClient(); print('DB OK' if db.test_connection() else 'DB FAILED')"

# Check Redis connection
python -c "import redis; r = redis.Redis(); print('Redis OK' if r.ping() else 'Redis FAILED')"

# Check Airflow status
airflow dags list
```

### 2. Monitoring Dashboards
- **Airflow UI**: http://localhost:8080
- **ClickHouse UI**: http://localhost:8123
- **Prometheus**: http://localhost:9090 (if enabled)

### 3. Log Management
```bash
# View application logs
tail -f logs/aliai.log

# View Airflow logs
tail -f airflow/logs/scheduler/latest/scheduler.log

# Rotate logs
logrotate /etc/logrotate.d/aliai
```

### 4. Data Maintenance
```bash
# Clean old data
python scripts/cleanup_old_data.py

# Backup database
clickhouse-backup create backup_name

# Restore database
clickhouse-backup restore backup_name
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed
```bash
# Check ClickHouse status
sudo systemctl status clickhouse-server

# Check ClickHouse logs
sudo tail -f /var/log/clickhouse-server/clickhouse-server.log

# Test connection
clickhouse-client --query "SELECT 1"
```

#### 2. Scraping Rate Limited
```bash
# Reduce concurrent requests
export MAX_CONCURRENT_REQUESTS=5
export REQUEST_DELAY=2.0

# Use proxy rotation
export PROXY_ENABLED=true
export PROXY_LIST=proxy1:port,proxy2:port
```

#### 3. AI Analysis Failed
```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Test API connection
python -c "import openai; openai.api_key='$OPENAI_API_KEY'; print(openai.models.list())"

# Use local models as fallback
export MOCK_AI_RESPONSES=true
```

#### 4. Airflow DAGs Not Running
```bash
# Check Airflow scheduler
airflow scheduler --daemon

# Check DAG status
airflow dags list

# Manually trigger DAG
airflow dags trigger aliexpress_daily_scraping
```

### Performance Optimization

#### 1. Database Optimization
```sql
-- Optimize ClickHouse tables
OPTIMIZE TABLE products FINAL;
OPTIMIZE TABLE reviews FINAL;

-- Add indexes for better performance
CREATE INDEX idx_products_price ON products (price) TYPE minmax GRANULARITY 1;
CREATE INDEX idx_products_rating ON products (average_rating) TYPE minmax GRANULARITY 1;
```

#### 2. Scraping Optimization
```python
# Use connection pooling
connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)

# Enable compression
headers = {'Accept-Encoding': 'gzip, deflate'}

# Use persistent sessions
async with aiohttp.ClientSession(connector=connector) as session:
    # Scraping operations
```

#### 3. Memory Optimization
```bash
# Increase ClickHouse memory limits
echo "max_memory_usage = 8000000000" >> /etc/clickhouse-server/config.xml

# Use batch processing
export BATCH_SIZE=1000
export PROCESSING_THREADS=4
```

### Security Considerations

#### 1. API Key Security
```bash
# Store API keys securely
export OPENAI_API_KEY=$(cat /secure/openai_key.txt)

# Use environment-specific configs
cp .env.production .env
```

#### 2. Database Security
```sql
-- Create dedicated user
CREATE USER aliai_user IDENTIFIED BY 'secure_password';
GRANT ALL ON aliexpress.* TO aliai_user;

-- Enable SSL
SET allow_experimental_ssl = 1;
```

#### 3. Network Security
```bash
# Use VPN for scraping
export PROXY_ENABLED=true
export PROXY_LIST=vpn_proxy:port

# Rate limit API calls
export RATE_LIMIT_PER_MINUTE=30
```

This comprehensive setup guide should help you deploy and maintain the AliAI system successfully. For additional support, refer to the troubleshooting section or check the project documentation.
