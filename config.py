DECLINE_THRESHOLD_PCT  = 20.0   # Server-side minimum; UI defaults to 50 % but user can change
MIN_MARKET_CAP_B       = 1.0    # Server-side minimum in $B; UI can filter higher
BATCH_SIZE             = 25     # Tickers per yfinance batch download
BATCH_DELAY_SECONDS    = 3      # Polite delay between batches
CACHE_MAX_AGE_HOURS    = 20     # Re-fetch if cache older than this
CACHE_DIR              = "cache"
DOCS_DIR               = "docs"
TEMPLATE_PATH          = "templates/report.html.j2"
