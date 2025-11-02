-- Migration: 002_master_products_table.sql
-- Description: Master product ID table for discovering and tracking products without full details
-- Created: Added for master product discovery pipeline

-- Master products table - Lightweight table for discovered product IDs
CREATE TABLE IF NOT EXISTS master_products (
    product_id String,
    product_url String,
    category_id String,
    category_name String,
    discovered_at DateTime DEFAULT now(),
    last_scraped_at Nullable(DateTime),
    scrape_status String DEFAULT 'pending', -- 'pending', 'scraped', 'failed', 'skipped'
    scrape_priority UInt8 DEFAULT 5, -- Priority for scraping (1-10)
    error_count UInt8 DEFAULT 0, -- Failed scrape attempts
    is_active UInt8 DEFAULT 1 -- Whether product is still available
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(discovered_at)
ORDER BY (category_id, product_id, discovered_at)
SETTINGS index_granularity = 8192;

-- Create materialized view for products needing updates
CREATE MATERIALIZED VIEW IF NOT EXISTS master_products_to_scrape
ENGINE = SummingMergeTree()
ORDER BY (product_id, category_id)
AS SELECT
    product_id,
    product_url,
    category_id,
    category_name,
    scrape_priority,
    error_count,
    count() as occurrences,
    max(discovered_at) as last_discovered_at
FROM master_products
WHERE scrape_status = 'pending' AND is_active = 1
GROUP BY product_id, product_url, category_id, category_name, scrape_priority, error_count;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_master_products_status ON master_products (scrape_status) TYPE minmax GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_master_products_priority ON master_products (scrape_priority) TYPE minmax GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_master_products_active ON master_products (is_active) TYPE minmax GRANULARITY 1;
CREATE INDEX IF NOT EXISTS idx_master_products_category ON master_products (category_id) TYPE bloom_filter(0.01) GRANULARITY 1;

-- Create index for finding products to update based on last_scraped_at
CREATE INDEX IF NOT EXISTS idx_master_products_last_scraped ON master_products (last_scraped_at) TYPE minmax GRANULARITY 1;

