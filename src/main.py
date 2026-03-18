"""Orchestration entry point for the S&P 500 decline monitor."""

import os
import sys

import config
from src.fetch_tickers import get_sp500_tickers
from src.fetch_prices import fetch_all
from src.analyze import build_results
from src.render import render_report


def main() -> None:
    print("=== S&P 500 Decline Monitor ===")

    print("\n[1/4] Fetching S&P 500 ticker list...")
    tickers_df = get_sp500_tickers()

    print(f"\n[2/4] Fetching price data for {len(tickers_df)} tickers...")
    raw_data = fetch_all(tickers_df["ticker"].tolist())

    print("\n[3/4] Analysing declines...")
    results_df = build_results(raw_data, tickers_df)
    print(f"      Found {len(results_df)} stocks down ≥{config.DECLINE_THRESHOLD_PCT}% from ATH "
          f"with market cap ≥${config.MIN_MARKET_CAP_B}B.")

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
    # Allow running as: python -m src.main  OR  python src/main.py
    sys.exit(main())
