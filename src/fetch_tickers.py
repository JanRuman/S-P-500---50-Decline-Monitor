"""Fetch the S&P 500 constituent list from Wikipedia."""

import io
import os

import pandas as pd
import requests

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
FALLBACK_CSV = os.path.join("cache", "sp500_tickers.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; sp500-monitor/1.0; "
        "+https://github.com/JanRuman/S-P-500---50-Decline-Monitor)"
    )
}


def get_sp500_tickers() -> pd.DataFrame:
    """Return DataFrame with columns [ticker, name, sector].

    Tries Wikipedia first; falls back to a cached CSV snapshot.
    """
    try:
        response = requests.get(WIKIPEDIA_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        tables = pd.read_html(io.StringIO(response.text), attrs={"id": "constituents"})
        df = tables[0]
        df = df.rename(columns={
            "Symbol": "ticker",
            "Security": "name",
            "GICS Sector": "sector",
        })
        df = df[["ticker", "name", "sector"]].copy()
        # yfinance uses hyphens, Wikipedia uses dots (e.g. BRK.B -> BRK-B)
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
        # Save a fresh snapshot for future fallback
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
            "Could not fetch S&P 500 tickers from Wikipedia and no fallback CSV found. "
            "Commit cache/sp500_tickers.csv to the repo as a bootstrap snapshot."
        ) from e
