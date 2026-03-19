"""Compute ATH decline metrics and filter/sort results."""

import pandas as pd

import config


def build_results(raw_data: dict[str, dict], tickers_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-ticker metrics and return filtered, sorted DataFrame.

    Args:
        raw_data: {ticker: {"hist": pd.Series|None, "market_cap": float|None}}
        tickers_df: DataFrame with columns [ticker, name, sector, exchange]

    Returns:
        Filtered DataFrame sorted by pct_decline descending.
    """
    meta = tickers_df.set_index("ticker")
    rows = []

    for ticker, data in raw_data.items():
        hist = data.get("hist")
        market_cap = data.get("market_cap")

        # Skip if no price history
        if hist is None or len(hist) == 0:
            continue

        current_price = float(hist.iloc[-1])
        ath_price = float(hist.max())

        if ath_price <= 0:
            continue

        pct_decline = (ath_price - current_price) / ath_price * 100
        ath_date = hist.idxmax()
        ath_date_str = (
            ath_date.strftime("%Y-%m-%d") if hasattr(ath_date, "strftime")
            else str(ath_date)[:10]
        )

        # Market cap — use 0 if unavailable so stock still appears
        market_cap_b = round(market_cap / 1e9, 2) if market_cap else 0.0

        # Server-side minimum decline filter only
        if pct_decline < config.DECLINE_THRESHOLD_PCT:
            continue

        # Server-side market cap filter (only when cap is known and threshold > 0)
        if config.MIN_MARKET_CAP_B > 0 and market_cap_b > 0:
            if market_cap_b < config.MIN_MARKET_CAP_B:
                continue

        name     = meta.at[ticker, "name"]     if ticker in meta.index else ticker
        sector   = meta.at[ticker, "sector"]   if ticker in meta.index else "Unknown"
        exchange = (
            meta.at[ticker, "exchange"]
            if ticker in meta.index and "exchange" in meta.columns
            else "Unknown"
        )

        # Severity
        if pct_decline >= 75:
            severity = "severe"
        elif pct_decline >= 50:
            severity = "significant"
        else:
            severity = "moderate"

        rows.append({
            "ticker":        ticker,
            "name":          name,
            "sector":        sector,
            "exchange":      exchange,
            "current_price": round(current_price, 2),
            "ath_price":     round(ath_price, 2),
            "ath_date":      ath_date_str,
            "pct_decline":   round(pct_decline, 1),
            "market_cap_b":  market_cap_b,
            "severity":      severity,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("pct_decline", ascending=False).reset_index(drop=True)
