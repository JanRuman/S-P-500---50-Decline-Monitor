DECLINE_THRESHOLD_PCT  = 20.0   # Server-side minimum; UI defaults to 50% but user can change
MIN_MARKET_CAP_B       = 0.0    # Server-side minimum in $B (0 = no filter); UI can filter higher
BATCH_SIZE             = 25     # Tickers per yfinance batch download
BATCH_DELAY_SECONDS    = 3      # Polite delay between batches
CACHE_MAX_AGE_HOURS    = 20     # Re-fetch if cache older than this
CACHE_DIR              = "cache"
DOCS_DIR               = "docs"
TEMPLATE_PATH          = "templates/report.html.j2"

# Custom tickers to monitor in addition to the main indexes.
# Use any valid Yahoo Finance ticker symbol.
# European stocks need exchange suffix: .DE (Germany), .PA (France), .AS (Netherlands) etc.
EXTRA_TICKERS = [
    {"ticker": "NVO",   "name": "Novo Nordisk A/S",    "sector": "Healthcare", "exchange": "Custom"},
    {"ticker": "TSM",   "name": "Taiwan Semiconductor", "sector": "Technology", "exchange": "Custom"},
    {"ticker": "BABA",  "name": "Alibaba Group",        "sector": "Consumer",   "exchange": "Custom"},
]
