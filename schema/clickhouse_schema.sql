-- ClickHouse Schema for AliExpress Product Analysis
-- Optimized for analytical queries and large-scale data processing

-- Products table - Core product information
CREATE TABLE products (
    product_id String,
    title String,
    price Decimal(10, 2),
    original_price Decimal(10, 2),
    discount_percentage UInt8,
    currency String DEFAULT 'USD',
    shipping_cost Decimal(10, 2),
    free_shipping UInt8 DEFAULT 0,
    seller_id String,
    seller_name String,
    seller_rating Decimal(3, 2),
    seller_followers UInt32,
    category_id String,
    category_name String,
    subcategory_id String,
    subcategory_name String,
    brand String,
    sku String,
    product_url String,
    image_urls Array(String),
    tags Array(String),
    specifications Map(String, String),
    total_reviews UInt32 DEFAULT 0,
    average_rating Decimal(3, 2) DEFAULT 0,
    total_sales UInt32 DEFAULT 0,
    stock_quantity UInt32,
    is_available UInt8 DEFAULT 1,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now(),
    scraped_at DateTime DEFAULT now(),
    seasonal_tags Array(String),
    trend_score Float32 DEFAULT 0,
    margin_potential Float32 DEFAULT 0
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(scraped_at)
ORDER BY (category_id, seller_id, scraped_at)
SETTINGS index_granularity = 8192;

-- Reviews table - User reviews and sentiment analysis
CREATE TABLE reviews (
    review_id String,
    product_id String,
    user_id String,
    user_name String,
    user_country String,
    rating UInt8,
    review_text String,
    review_date DateTime,
    helpful_votes UInt32 DEFAULT 0,
    verified_purchase UInt8 DEFAULT 0,
    sentiment_score Float32,
    sentiment_label String,
    key_phrases Array(String),
    language String,
    translated_text String,
    created_at DateTime DEFAULT now(),
    scraped_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(scraped_at)
ORDER BY (product_id, scraped_at)
SETTINGS index_granularity = 8192;

-- Categories table - Hierarchical product categorization
CREATE TABLE categories (
    category_id String,
    category_name String,
    parent_category_id String,
    level UInt8,
    path String,
    seasonal_relevance Map(String, Float32), -- season -> relevance_score
    trend_score Float32 DEFAULT 0,
    product_count UInt32 DEFAULT 0,
    avg_price Decimal(10, 2),
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (level, category_id)
SETTINGS index_granularity = 8192;

-- Sellers table - Seller/distributor information
CREATE TABLE sellers (
    seller_id String,
    seller_name String,
    store_url String,
    country String,
    seller_rating Decimal(3, 2),
    total_followers UInt32,
    total_products UInt32,
    years_active UInt8,
    response_rate Decimal(5, 2),
    response_time String,
    is_verified UInt8 DEFAULT 0,
    is_gold_supplier UInt8 DEFAULT 0,
    is_trade_assurance UInt8 DEFAULT 0,
    avg_shipping_time UInt8,
    total_sales UInt64,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (seller_id, created_at)
SETTINGS index_granularity = 8192;

-- Price history table - Track price changes over time
CREATE TABLE price_history (
    product_id String,
    price Decimal(10, 2),
    original_price Decimal(10, 2),
    discount_percentage UInt8,
    currency String,
    recorded_at DateTime,
    scraped_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(scraped_at)
ORDER BY (product_id, recorded_at)
SETTINGS index_granularity = 8192;

-- Trends table - Track trending products and categories
CREATE TABLE trends (
    trend_id String,
    product_id String,
    category_id String,
    trend_type String, -- 'seasonal', 'viral', 'price_drop', 'new_arrival'
    trend_score Float32,
    trend_direction String, -- 'up', 'down', 'stable'
    confidence_score Float32,
    detected_at DateTime,
    duration_days UInt16,
    peak_score Float32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(detected_at)
ORDER BY (trend_type, detected_at)
SETTINGS index_granularity = 8192;

-- Scraping logs table - Track scraping activities and performance
CREATE TABLE scraping_logs (
    log_id String,
    task_id String,
    url String,
    status String, -- 'success', 'failed', 'retry'
    response_time_ms UInt32,
    data_points_extracted UInt32,
    error_message String,
    proxy_used String,
    user_agent String,
    scraped_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(scraped_at)
ORDER BY (task_id, scraped_at)
SETTINGS index_granularity = 8192;

-- Create materialized views for common analytics queries

-- Top products by sales
CREATE MATERIALIZED VIEW top_products_by_sales
ENGINE = SummingMergeTree()
ORDER BY (category_id, seller_id)
AS SELECT
    category_id,
    seller_id,
    count() as product_count,
    sum(total_sales) as total_category_sales,
    avg(average_rating) as avg_category_rating,
    max(scraped_at) as last_updated
FROM products
GROUP BY category_id, seller_id;

-- Daily price changes
CREATE MATERIALIZED VIEW daily_price_changes
ENGINE = SummingMergeTree()
ORDER BY (product_id, toDate(scraped_at))
AS SELECT
    product_id,
    toDate(scraped_at) as date,
    avg(price) as avg_price,
    min(price) as min_price,
    max(price) as max_price,
    count() as price_points
FROM price_history
GROUP BY product_id, toDate(scraped_at);

-- Sentiment analysis summary
CREATE MATERIALIZED VIEW sentiment_summary
ENGINE = SummingMergeTree()
ORDER BY (product_id, toDate(scraped_at))
AS SELECT
    product_id,
    toDate(scraped_at) as date,
    count() as review_count,
    avg(sentiment_score) as avg_sentiment,
    countIf(sentiment_label = 'positive') as positive_reviews,
    countIf(sentiment_label = 'negative') as negative_reviews,
    countIf(sentiment_label = 'neutral') as neutral_reviews
FROM reviews
GROUP BY product_id, toDate(scraped_at);

-- Create indexes for better query performance
CREATE INDEX idx_products_price ON products (price) TYPE minmax GRANULARITY 1;
CREATE INDEX idx_products_rating ON products (average_rating) TYPE minmax GRANULARITY 1;
CREATE INDEX idx_reviews_sentiment ON reviews (sentiment_score) TYPE minmax GRANULARITY 1;
CREATE INDEX idx_price_history_date ON price_history (recorded_at) TYPE minmax GRANULARITY 1;
