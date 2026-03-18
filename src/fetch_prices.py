"""Fetch historical price data and market cap for a list of tickers.

Uses a per-ticker pickle cache to avoid redundant downloads.
Batches yfinance.download() calls to reduce HTTP requests and rate-limit risk.
"""

import os
import pickle
import time
from datetime import datetime, timezone, timedelta

import yfinance as yf

import config


def _cache_path(ticker: str) -> str:
    return os.path.join(config.CACHE_DIR, f"{ticker}.pkl")


def _load_cached(ticker: str) -> dict | None:
    """Return cached data if fresh, else None."""
    path = _cache_path(ticker)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        age = datetime.now(timezone.utc) - data["fetched_at"]
        if age < timedelta(hours=config.CACHE_MAX_AGE_HOURS):
            return data
    except Exception:
        pass
    return None


def _save_cached(ticker: str, data: dict) -> None:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    with open(_cache_path(ticker), "wb") as f:
        pickle.dump(data, f)


def _fetch_batch_history(tickers: list[str]) -> dict[str, object]:
    """Download max-period close history for a batch of tickers.

    Returns {ticker: pd.Series of Close prices}.
    """
    # yfinance.download with a list returns MultiIndex columns when >1 ticker
    raw = yf.download(
        tickers,
        period="max",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    result = {}
    if len(tickers) == 1:
        # Single-ticker result has flat columns
        close = raw.get("Close")
        if close is not None and not close.empty:
            result[tickers[0]] = close
    else:
        close_df = raw.get("Close")
        if close_df is not None:
            for ticker in tickers:
                if ticker in close_df.columns:
                    series = close_df[ticker].dropna()
                    if not series.empty:
                        result[ticker] = series
    return result


def _fetch_market_caps(tickers: list[str]) -> dict[str, float | None]:
    """Fetch market cap via fast_info for each ticker individually."""
    caps = {}
    for ticker in tickers:
        try:
            fi = yf.Ticker(ticker).fast_info
            caps[ticker] = getattr(fi, "market_cap", None)
        except Exception:
            caps[ticker] = None
    return caps


def fetch_all(tickers: list[str]) -> dict[str, dict]:
    """Return {ticker: {"hist": Series, "market_cap": float|None}} for all tickers.

    Uses cache where fresh; fetches missing/stale tickers in batches.
    """
    result: dict[str, dict] = {}
    to_fetch: list[str] = []

    for ticker in tickers:
        cached = _load_cached(ticker)
        if cached:
            result[ticker] = cached
        else:
            to_fetch.append(ticker)

    if not to_fetch:
        print("All tickers served from cache.")
        return result

    print(f"Fetching {len(to_fetch)} tickers in batches of {config.BATCH_SIZE}...")
    batches = [
        to_fetch[i : i + config.BATCH_SIZE]
        for i in range(0, len(to_fetch), config.BATCH_SIZE)
    ]

    for batch_num, batch in enumerate(batches, 1):
        print(f"  Batch {batch_num}/{len(batches)}: {len(batch)} tickers")
        # Retry with exponential backoff
        for attempt in range(3):
            try:
                histories = _fetch_batch_history(batch)
                break
            except Exception as e:
                if attempt == 2:
                    print(f"    WARNING: batch failed after 3 attempts ({e})")
                    histories = {}
                    break
                sleep_sec = 2 ** attempt * 10
                print(f"    Retry {attempt + 1} after {sleep_sec}s ({e})")
                time.sleep(sleep_sec)

        market_caps = _fetch_market_caps(batch)

        now = datetime.now(timezone.utc)
        for ticker in batch:
            hist = histories.get(ticker)
            data = {
                "fetched_at": now,
                "hist": hist,
                "market_cap": market_caps.get(ticker),
            }
            _save_cached(ticker, data)
            result[ticker] = data

        if batch_num < len(batches):
            time.sleep(config.BATCH_DELAY_SECONDS)

    print(f"Done. {len(result)} tickers available ({len(to_fetch) - len([t for t in to_fetch if result.get(t, {}).get('hist') is None])} with data).")
    return result
