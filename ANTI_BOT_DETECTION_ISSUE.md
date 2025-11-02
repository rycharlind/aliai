# AliExpress Anti-Bot Detection Issue

## Problem

The product discovery system is returning **0 products** from all AliExpress category pages due to aggressive anti-bot detection.

## Root Cause

AliExpress uses sophisticated bot detection that blocks automated requests, even when using:
- Standard HTTP requests (aiohttp/requests)
- Selenium with undetected Chrome
- Various User-Agent strings
- Rate limiting

When the scraper attempts to access category pages like `https://www.aliexpress.com/category/100003070/electronics.html`, AliExpress returns a JavaScript redirect to a captcha page instead of actual product listings.

### Evidence

```
Status: 200
Content: <script>sessionStorage.x5referer = window.location.href;var url = window.location.protocol + "//www.aliexpress.com//category/.../punish?..."
Page Title: "Captcha Interception"
```

## Current System

The codebase has two scraping approaches:
1. **`AliExpressScraper`** (main) - Uses aiohttp (lightweight, blocked by AliExpress)
2. **`simple_scraper.py`** - Uses Selenium with undetected Chrome (also blocked)

Both are being detected and redirected to captcha pages.

## Solutions

### 1. **API Access (Recommended)**
- Use AliExpress Partner/DSR API for official data access
- Requires business partnership or merchant account
- Most reliable and legal approach

### 2. **Residential Proxies + Captcha Solving**
- Use rotating residential proxies (e.g., Bright Data, Oxylabs)
- Integrate captcha solving service (e.g., 2Captcha, AntiCaptcha)
- Implement stealth browser fingerprinting
- **Cost**: $200-1000/month depending on volume

### 3. **Browser Fingerprinting & Stealth**
- Use advanced libraries like:
  - `playwright-stealth` for Playwright
  - Configure realistic browser fingerprints
  - Implement proper cookie management
  - Add random delays and human-like behavior
- **Note**: May still get blocked intermittently

### 4. **Alternative Data Sources**
- Scrape affiliate network feeds
- Use AliExpress RSS feeds (if available)
- Purchase data from third-party providers
- Use social media product discovery

### 5. **Hybrid Approach**
- Manually seed initial product IDs
- Scrape product detail pages (often less protected than listings)
- Use search instead of category pages
- Implement gradual, low-volume scraping

## Immediate Workaround

For development/testing, consider:

1. **Manual Product IDs**: Add known product IDs directly to `master_products` table
2. **Mock Data**: Generate test data for development
3. **Search Instead**: Try search URLs instead of category pages
4. **Different Domain**: Try `aliexpress.us` instead of `aliexpress.com`

## Testing Search URLs

Category pages are heavily protected. Try these alternative approaches:

```python
# Search instead of category
search_url = "https://www.aliexpress.com/wholesale?SearchText=phone"

# Different domain
us_url = "https://www.aliexpress.us/category/100003070/electronics.html"

# Product pages (less protected than listings)
product_url = "https://www.aliexpress.com/item/3256810016116999.html"
```

## Recommendations

1. **For Production**: Implement residential proxies + captcha solving
2. **For Development**: Use mock data or manual seeding
3. **Long-term**: Explore official API access or alternative data sources
4. **Monitoring**: Add detection metrics to track success rate

## Files to Modify

If implementing anti-bot bypass:

- `aliai/scraper.py` - Main scraping logic
- `aliai/config.py` - Add proxy/captcha configuration
- `requirements.txt` - Add stealth libraries
- `.env` - Configure proxy credentials

## Next Steps

1. Decide on approach (API, proxies, or alternatives)
2. Update scraping infrastructure
3. Add detection/bounce rate monitoring
4. Implement fallback strategies
5. Document scraping policies

## BREAKTHROUGH: Search Pages Work!

**UPDATE**: Testing has revealed that while **category pages are heavily protected**, **search pages work** with proper Selenium configuration:

```python
# Category pages: BLOCKED ❌
category_url = "https://www.aliexpress.com/category/100003070/electronics.html"

# Search pages: WORKING ✅
search_url = "https://www.aliexpress.com/wholesale?SearchText=phone&page=1"
```

### What Works

1. **Non-headless Selenium** with `undetected_chromedriver`
2. **Search URLs** instead of category pages
3. **Proper wait times** (15+ seconds for JavaScript rendering)
4. **Real browser settings** (maximized, proper user-agent)

### Test Results

Successfully extracted **33 product IDs** from a search page for "phone"!

### Recommended Fix

Modify the discovery system to use search queries instead of category URLs:

```python
# Instead of: category_url
# Use: search_url based on category keywords

# Example mapping:
electronics_terms = ["phone", "laptop", "tablet", "headphones"]
clothing_terms = ["t-shirt", "jeans", "shoes", "jacket"]
```

This approach can discover products while the category pages are blocked.

