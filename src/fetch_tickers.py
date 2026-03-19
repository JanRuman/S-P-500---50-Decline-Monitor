"""Fetch S&P 500 and NASDAQ-100 constituent lists from Wikipedia."""

import io
import os

import pandas as pd
import requests

import config

WIKIPEDIA_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKIPEDIA_NDX_URL   = "https://en.wikipedia.org/wiki/Nasdaq-100"
FALLBACK_CSV        = os.path.join("cache", "tickers.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _fetch_html(url: str) -> str:
    session = requests.Session()
    response = session.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def _get_sp500() -> pd.DataFrame:
    html = _fetch_html(WIKIPEDIA_SP500_URL)
    tables = pd.read_html(io.StringIO(html), attrs={"id": "constituents"})
    df = tables[0]
    df = df.rename(columns={"Symbol": "ticker", "Security": "name", "GICS Sector": "sector"})
    df = df[["ticker", "name", "sector"]].copy()
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    df["exchange"] = "S&P 500"
    return df


def _get_nasdaq100() -> pd.DataFrame:
    html = _fetch_html(WIKIPEDIA_NDX_URL)
    try:
        tables = pd.read_html(io.StringIO(html), attrs={"id": "constituents"})
        df = tables[0]
    except Exception:
        tables = pd.read_html(io.StringIO(html))
        df = None
        for t in tables:
            cols_lower = [str(c).lower() for c in t.columns]
            if any(k in cols_lower for k in ["ticker", "symbol"]):
                df = t
                break
        if df is None:
            raise RuntimeError("Could not find NASDAQ-100 table on Wikipedia.")

    col_map = {}
    for col in df.columns:
        cl = str(col).lower()
        if cl in ("ticker", "symbol"):
            col_map[col] = "ticker"
        elif cl in ("company", "security", "name"):
            col_map[col] = "name"
        elif "sector" in cl:
            col_map[col] = "sector"
    df = df.rename(columns=col_map)

    if "ticker" not in df.columns:
        raise RuntimeError(f"No ticker column found. Columns: {list(df.columns)}")
    if "name" not in df.columns:
        df["name"] = df["ticker"]
    if "sector" not in df.columns:
        df["sector"] = "Technology"

    df = df[["ticker", "name", "sector"]].copy()
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False).str.strip()
    df["exchange"] = "NASDAQ-100"
    return df


def _get_extra() -> pd.DataFrame:
    """Return the manually configured extra tickers from config.EXTRA_TICKERS."""
    if not getattr(config, "EXTRA_TICKERS", None):
        return pd.DataFrame(columns=["ticker", "name", "sector", "exchange"])
    df = pd.DataFrame(config.EXTRA_TICKERS)
    for col in ["ticker", "name", "sector", "exchange"]:
        if col not in df.columns:
            df[col] = "Unknown"
    return df[["ticker", "name", "sector", "exchange"]]


def get_tickers() -> pd.DataFrame:
    """Return combined S&P 500 + NASDAQ-100 + Extra DataFrame.

    Columns: ticker, name, sector, exchange.
    Falls back to cached CSV if Wikipedia is unreachable.
    """
    errors = []
    sp500_df = nasdaq_df = None

    try:
        sp500_df = _get_sp500()
        print(f"  S&P 500:    {len(sp500_df)} tickers from Wikipedia.")
    except Exception as e:
        errors.append(f"S&P 500: {e}")
        print(f"  WARNING: S&P 500 fetch failed ({e})")

    try:
        nasdaq_df = _get_nasdaq100()
        print(f"  NASDAQ-100: {len(nasdaq_df)} tickers from Wikipedia.")
    except Exception as e:
        errors.append(f"NASDAQ-100: {e}")
        print(f"  WARNING: NASDAQ-100 fetch failed ({e})")

    extra_df = _get_extra()
    if not extra_df.empty:
        print(f"  Extra:      {len(extra_df)} tickers from config.")

    parts = [df for df in [sp500_df, nasdaq_df, extra_df] if df is not None and not df.empty]

    if parts:
        combined = pd.concat(parts, ignore_index=True)
        # Keep first occurrence when a ticker appears in multiple indexes
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

    raise RuntimeError(
        "Could not fetch tickers from Wikipedia and no fallback CSV found.\n"
        f"Errors: {'; '.join(errors)}"
    )


# Backward-compatibility alias
def get_sp500_tickers() -> pd.DataFrame:
    return get_tickers()
