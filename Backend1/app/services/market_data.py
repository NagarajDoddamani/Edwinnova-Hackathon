"""
app/services/market_data.py
────────────────────────────
Fetches real-time Indian market data from Yahoo Finance.
No API key needed.
"""

import httpx
from datetime import datetime


async def get_market_data() -> dict:
    symbols = {
        "NIFTY50":   "^NSEI",
        "SENSEX":    "^BSESN",
        "GOLD":      "GOLDBEES.NS",
        "SILVER":    "SILVERBEES.NS",
        "USD_INR":   "INR=X",
        "NIFTYBANK": "^NSEBANK",
    }

    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name, symbol in symbols.items():
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                data = resp.json()
                meta = data["chart"]["result"][0]["meta"]
                results[name] = {
                    "price":   round(meta.get("regularMarketPrice", 0), 2),
                    "change":  round(meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0), 2),
                    "change_pct": round(
                        ((meta.get("regularMarketPrice", 0) - meta.get("previousClose", 0))
                         / meta.get("previousClose", 1)) * 100, 2
                    ),
                    "currency": meta.get("currency", "INR"),
                }
            except Exception:
                results[name] = {"price": 0, "change": 0, "change_pct": 0, "currency": "INR"}

    results["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return results