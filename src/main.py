"""Orchestration entry point for the S&P 500 + NASDAQ-100 decline monitor."""

import os
import sys

import config
from src.fetch_tickers import get_tickers
from src.fetch_prices import fetch_all
from src.analyze import build_results
from src.render import render_report


def main() -> None:
    print("=== S&P 500 + NASDAQ-100 Decline Monitor ===")

    print("\n[1/4] Fetching ticker lists (S&P 500 + NASDAQ-100 + Extra)...")
    tickers_df = get_tickers()
    print(f"      Tickers loaded: {len(tickers_df)}")
    print(f"      Columns: {list(tickers_df.columns)}")
    print(f"      Sample tickers: {tickers_df['ticker'].head(5).tolist()}")

    print(f"\n[2/4] Fetching price data for {len(tickers_df)} tickers...")
    raw_data = fetch_all(tickers_df["ticker"].tolist())

    # Debug: count how many tickers have valid data
    has_hist  = sum(1 for d in raw_data.values() if d.get("hist") is not None and len(d.get("hist", [])) > 0)
    has_cap   = sum(1 for d in raw_data.values() if d.get("market_cap") is not None)
    print(f"      Tickers with price history: {has_hist}/{len(raw_data)}")
    print(f"      Tickers with market cap:    {has_cap}/{len(raw_data)}")

    print("\n[3/4] Analysing declines...")
    results_df = build_results(raw_data, tickers_df)
    print(f"      Found {len(results_df)} stocks down ≥{config.DECLINE_THRESHOLD_PCT}% from ATH "
          f"with market cap ≥${config.MIN_MARKET_CAP_B}B.")
    if not results_df.empty:
        print(f"      Top 5 declines: {results_df[['ticker','pct_decline']].head().to_dict('records')}")

    print("\n[4/4] Generating HTML report...")
    html = render_report(results_df)

    os.makedirs(config.DOCS_DIR, exist_ok=True)
    out_path = os.path.join(config.DOCS_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"      Report written to {out_path}")

    skipped = sum(
        1 for t in tickers_df["ticker"]
        if raw_data.get(t, {}).get("hist") is None
    )
    if skipped:
        print(f"\nWARNING: {skipped} tickers had no price data and were skipped.")

    print("\nDone.")


if __name__ == "__main__":
    sys.exit(main())
