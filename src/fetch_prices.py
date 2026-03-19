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
        # Reject cache entries with no price data (from old failed runs)
        if data.get("hist") is None or len(data.get("hist", [])) == 0:
            return None
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
    """Download max-period close history for a batch of tickers."""
    raw = yf.download(
        tickers,
        period="max",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    result = {}
    if len(tickers) == 1:
        close = raw.get("Close")
        if close is not None and not close.empty:
            result[tickers[0]] = close.dropna()
    else:
        close_df = raw.get("Close")
        if close_df is not None:
            for ticker in tickers:
                if ticker in close_df.columns:
                    series = close_df[ticker].dropna()
                    if not series.empty:
                        result[ticker] = series
    return result


def _get_market_cap(ticker: str) -> float | None:
    """Safely fetch market cap, trying multiple yfinance attributes."""
    try:
        t = yf.Ticker(ticker)
        # Try fast_info first (faster but can crash on bad timezone data)
        try:
            cap = t.fast_info.market_cap
            if cap and cap > 0:
                return float(cap)
        except Exception:
            pass
        # Fall back to .info dict (slower but more robust)
        info = t.info
        cap = info.get("marketCap") or info.get("market_cap")
        if cap and cap > 0:
            return float(cap)
    except Exception:
        pass
    return None


def _fetch_market_caps(tickers: list[str]) -> dict[str, float | None]:
    """Fetch market cap for each ticker individually."""
    caps = {}
    for ticker in tickers:
        caps[ticker] = _get_market_cap(ticker)
    return caps


def fetch_all(tickers: list[str]) -> dict[str, dict]:
    """Return {ticker: {"hist": Series, "market_cap": float|None}} for all tickers."""
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
        to_fetch[i: i + config.BATCH_SIZE]
        for i in range(0, len(to_fetch), config.BATCH_SIZE)
    ]

    for batch_num, batch in enumerate(batches, 1):
        print(f"  Batch {batch_num}/{len(batches)}: {len(batch)} tickers")
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

        success = sum(1 for t in batch if histories.get(t) is not None)
        print(f"    Price data: {success}/{len(batch)} tickers OK")

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

    with_data = sum(1 for t in to_fetch if result.get(t, {}).get("hist") is not None)
    print(f"Done. {with_data}/{len(to_fetch)} fetched tickers have price history.")
    return result
