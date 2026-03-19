"""Fetch S&P 500, NASDAQ-100, EURO STOXX 50 and DAX constituent lists."""

import io
import os

import pandas as pd
import requests

import config

WIKIPEDIA_SP500_URL      = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKIPEDIA_NDX_URL        = "https://en.wikipedia.org/wiki/Nasdaq-100"
WIKIPEDIA_EUROSTOXX_URL  = "https://en.wikipedia.org/wiki/Euro_Stoxx_50"
WIKIPEDIA_DAX_URL        = "https://en.wikipedia.org/wiki/DAX"
FALLBACK_CSV             = os.path.join("cache", "tickers.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Map country name → Yahoo Finance exchange suffix for European stocks
COUNTRY_SUFFIX = {
    "Germany":     ".DE",
    "France":      ".PA",
    "Netherlands": ".AS",
    "Spain":       ".MC",
    "Italy":       ".MI",
    "Belgium":     ".BR",
    "Finland":     ".HE",
    "Ireland":     ".IR",
    "Luxembourg":  ".LU",
    "Portugal":    ".LS",
    "Austria":     ".VI",
}


def _fetch_html(url: str) -> str:
    session = requests.Session()
    response = session.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def _find_table(html: str, table_id: str | None = None) -> pd.DataFrame:
    """Try to find table by id first, then by sniffing for ticker/symbol column."""
    if table_id:
        try:
            tables = pd.read_html(io.StringIO(html), attrs={"id": table_id})
            return tables[0]
        except Exception:
            pass
    tables = pd.read_html(io.StringIO(html))
    for t in tables:
        cols_lower = [str(c).lower() for c in t.columns]
        # Use substring match so "ticker symbol", "stock symbol" etc. all match
        if any("ticker" in c or "symbol" in c for c in cols_lower):
            return t
    raise RuntimeError("No suitable table found on page.")


def _normalise(df: pd.DataFrame, exchange: str) -> pd.DataFrame:
    """Rename columns to [ticker, name, sector] and tag exchange."""
    col_map = {}
    for col in df.columns:
        cl = str(col).lower()
        # Substring matches handle "Ticker symbol", "Stock symbol", "Company name" etc.
        if ("ticker" in cl or "symbol" in cl) and "ticker" not in col_map.values():
            col_map[col] = "ticker"
        elif ("company" in cl or "security" in cl or cl == "name") and "name" not in col_map.values():
            col_map[col] = "name"
        elif "sector" in cl and "sector" not in col_map.values():
            col_map[col] = "sector"
    df = df.rename(columns=col_map)
    if "ticker" not in df.columns:
        raise RuntimeError(f"No ticker column found. Columns: {list(df.columns)}")
    if "name"   not in df.columns:
        df["name"]   = df["ticker"]
    if "sector" not in df.columns:
        df["sector"] = "Unknown"
    df = df[["ticker", "name", "sector"]].copy()
    df["ticker"]   = df["ticker"].str.strip().str.replace(".", "-", regex=False)
    df["exchange"] = exchange
    return df


def _get_sp500() -> pd.DataFrame:
    html = _fetch_html(WIKIPEDIA_SP500_URL)
    df = _find_table(html, table_id="constituents")
    df = df.rename(columns={"Symbol": "ticker", "Security": "name", "GICS Sector": "sector"})
    df = df[["ticker", "name", "sector"]].copy()
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    df["exchange"] = "S&P 500"
    return df


def _get_nasdaq100() -> pd.DataFrame:
    html = _fetch_html(WIKIPEDIA_NDX_URL)
    df = _find_table(html, table_id="constituents")
    return _normalise(df, "NASDAQ-100")


def _get_eurostoxx50() -> pd.DataFrame:
    """Fetch EURO STOXX 50 and append correct Yahoo Finance exchange suffixes."""
    html = _fetch_html(WIKIPEDIA_EUROSTOXX_URL)
    df = _find_table(html, table_id="constituents")

    # Find country column if present
    country_col = None
    for col in df.columns:
        if str(col).lower() in ("country", "nation"):
            country_col = col
            break

    col_map = {}
    for col in df.columns:
        cl = str(col).lower()
        if cl in ("ticker", "symbol") and "ticker" not in col_map.values():
            col_map[col] = "ticker"
        elif cl in ("company", "security", "name") and "name" not in col_map.values():
            col_map[col] = "name"
        elif "sector" in cl and "sector" not in col_map.values():
            col_map[col] = "sector"
    df = df.rename(columns=col_map)

    if "ticker" not in df.columns:
        raise RuntimeError(f"No ticker column in EURO STOXX 50. Columns: {list(df.columns)}")
    if "name"   not in df.columns:
        df["name"]   = df["ticker"]
    if "sector" not in df.columns:
        df["sector"] = "Unknown"

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.strip()

    # Add Yahoo Finance suffix based on country
    if country_col:
        def add_suffix(row):
            ticker = row["ticker"]
            if "." in ticker or ticker.endswith(tuple(COUNTRY_SUFFIX.values())):
                return ticker  # already has suffix
            country = str(row.get(country_col, ""))
            suffix = COUNTRY_SUFFIX.get(country, ".DE")  # default .DE for unknown
            return ticker + suffix
        df["ticker"] = df.apply(add_suffix, axis=1)
    else:
        # No country column — assume German (most EURO STOXX 50 components are German)
        df["ticker"] = df["ticker"].apply(
            lambda t: t if ("." in t) else t + ".DE"
        )

    df["exchange"] = "EURO STOXX 50"
    return df[["ticker", "name", "sector", "exchange"]]


def _get_dax() -> pd.DataFrame:
    """Fetch DAX 40 and append .DE Yahoo Finance suffix."""
    html = _fetch_html(WIKIPEDIA_DAX_URL)
    df = _find_table(html, table_id="constituents")
    df = _normalise(df, "DAX")
    # All DAX stocks trade on Frankfurt (XETRA) → .DE suffix
    df["ticker"] = df["ticker"].apply(
        lambda t: t if ("." in t) else t + ".DE"
    )
    return df


def _get_extra() -> pd.DataFrame:
    """Return manually configured extra tickers from config.EXTRA_TICKERS."""
    if not getattr(config, "EXTRA_TICKERS", None):
        return pd.DataFrame(columns=["ticker", "name", "sector", "exchange"])
    df = pd.DataFrame(config.EXTRA_TICKERS)
    for col in ["ticker", "name", "sector", "exchange"]:
        if col not in df.columns:
            df[col] = "Unknown"
    return df[["ticker", "name", "sector", "exchange"]]


def get_tickers() -> pd.DataFrame:
    """Return combined S&P 500 + NASDAQ-100 + EURO STOXX 50 + DAX + Custom tickers.

    Columns: ticker, name, sector, exchange.
    Falls back to cached CSV if Wikipedia is unreachable.
    """
    fetchers = [
        ("S&P 500",      _get_sp500),
        ("NASDAQ-100",   _get_nasdaq100),
        ("EURO STOXX 50",_get_eurostoxx50),
        ("DAX",          _get_dax),
    ]

    parts = []
    for label, fn in fetchers:
        try:
            df = fn()
            print(f"  {label:15s}: {len(df)} tickers from Wikipedia.")
            parts.append(df)
        except Exception as e:
            print(f"  WARNING: {label} fetch failed ({e})")

    extra_df = _get_extra()
    if not extra_df.empty:
        print(f"  {'Custom':15s}: {len(extra_df)} tickers from config.")
        parts.append(extra_df)

    if parts:
        combined = pd.concat(parts, ignore_index=True)
        combined = combined.drop_duplicates(subset="ticker", keep="first")
        os.makedirs("cache", exist_ok=True)
        combined.to_csv(FALLBACK_CSV, index=False)
        print(f"  Total unique tickers: {len(combined)}")
        return combined

    # All fetches failed — try fallback CSV
    print("All Wikipedia fetches failed, trying fallback CSV.")
    if os.path.exists(FALLBACK_CSV):
        df = pd.read_csv(FALLBACK_CSV)
        if "exchange" not in df.columns:
            df["exchange"] = "Unknown"
        print(f"Loaded {len(df)} tickers from fallback CSV.")
        return df

    raise RuntimeError("Could not fetch tickers and no fallback CSV found.")


# Backward-compatibility alias
def get_sp500_tickers() -> pd.DataFrame:
    return get_tickers()
