DECLINE_THRESHOLD_PCT = 50.0      # % decline from ATH to include
MIN_MARKET_CAP_B = 2.0            # Minimum market cap in billions
BATCH_SIZE = 25                   # Tickers per yfinance batch download
BATCH_DELAY_SECONDS = 3           # Polite delay between batches
CACHE_MAX_AGE_HOURS = 20          # Re-fetch if cache older than this
CACHE_DIR = "cache"
DOCS_DIR = "docs"
TEMPLATE_PATH = "templates/report.html.j2"
