"""Quick smoke-test: verify yfinance can reach Yahoo Finance."""
import yfinance as yf

print("=== yfinance smoke test ===")
t = yf.Ticker("AAPL")
hist = yf.download("AAPL", period="5d", auto_adjust=True, progress=False)
fi = t.fast_info
print(f"AAPL close rows : {len(hist)}")
print(f"AAPL market_cap : {getattr(fi, 'market_cap', 'N/A')}")
print(f"AAPL last_price : {getattr(fi, 'last_price', 'N/A')}")
print("=== smoke test done ===")
