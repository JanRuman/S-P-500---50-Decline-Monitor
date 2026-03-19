"""Fetch the S&P 500 constituent list."""

import io
import os

import pandas as pd
import requests

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
FALLBACK_CSV = os.path.join("cache", "sp500_tickers.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def get_sp500_tickers() -> pd.DataFrame:
    """Return DataFrame with columns [ticker, name, sector].
    Tries Wikipedia first; falls back to a cached CSV snapshot.
    """
    try:
        session = requests.Session()
        response = session.get(WIKIPEDIA_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text), attrs={"id": "constituents"})
        df = tables[0]
        df = df.rename(columns={
            "Symbol": "ticker",
            "Security": "name",
            "GICS Sector": "sector",
        })
        df = df[["ticker", "name", "sector"]].copy()
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
        os.makedirs("cache", exist_ok=True)
        df.to_csv(FALLBACK_CSV, index=False)
        print(f"Fetched {len(df)} tickers from Wikipedia.")
        return df
    except Exception as e:
        print(f"Wikipedia fetch failed ({e}), trying fallback CSV.")
        if os.path.exists(FALLBACK_CSV):
            df = pd.read_csv(FALLBACK_CSV)
            print(f"Loaded {len(df)} tickers from fallback CSV.")
            return df
        raise RuntimeError(
            "Could not fetch tickers. No fallback CSV found."
        ) from e
