DECLINE_THRESHOLD_PCT  = 20.0   # Server-side minimum; UI defaults to 50% but user can change
MIN_MARKET_CAP_B       = 0.0    # Server-side minimum in $B (0 = no filter); UI can filter higher
BATCH_SIZE             = 25     # Tickers per yfinance batch download
BATCH_DELAY_SECONDS    = 3      # Polite delay between batches
CACHE_MAX_AGE_HOURS    = 20     # Re-fetch if cache older than this
CACHE_DIR              = "cache"
DOCS_DIR               = "docs"
TEMPLATE_PATH          = "templates/report.html.j2"

# Extra tickers to monitor beyond S&P 500 + NASDAQ-100
# These can be any Yahoo Finance ticker (US or international ADRs etc.)
EXTRA_TICKERS = [
    # International stocks (as traded on US exchanges or Yahoo Finance)
    {"ticker": "NVO",  "name": "Novo Nordisk A/S",       "sector": "Healthcare",  "exchange": "Extra"},
    {"ticker": "ASML", "name": "ASML Holding N.V.",       "sector": "Technology",  "exchange": "Extra"},
    {"ticker": "TSM",  "name": "Taiwan Semiconductor",    "sector": "Technology",  "exchange": "Extra"},
    {"ticker": "BABA", "name": "Alibaba Group",           "sector": "Consumer",    "exchange": "Extra"},
    {"ticker": "SAP",  "name": "SAP SE",                  "sector": "Technology",  "exchange": "Extra"},
]
