"""Computes "what share of the S&P 500's total market cap is the
Magnificent 7" by summing real, live market caps for all current S&P 500
constituents (pulled from Wikipedia's constituent list, cross-referenced
against Yahoo Finance) rather than relying on a hardcoded/stale reference
figure that would silently go out of date.

Offline/periodic only - never runs per-visitor, so the ~500 sequential
lookups (a couple of minutes) cost nothing and don't affect anyone's
experience of the live site.
"""
import io
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import MAGNIFICENT_7

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "output"

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def fetch_sp500_symbols() -> list[str]:
    resp = requests.get(WIKI_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    table = pd.read_html(io.StringIO(resp.text))[0]
    # Wikipedia uses dot notation (BRK.B); Yahoo Finance expects hyphens (BRK-B)
    return [s.replace(".", "-") for s in table["Symbol"].tolist()]


def market_cap(ticker: str) -> float | None:
    try:
        info = yf.Ticker(ticker).fast_info
        mc = info.get("marketCap") or info.get("market_cap")
        return float(mc) if mc else None
    except Exception:
        return None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching S&P 500 constituent list...")
    symbols = fetch_sp500_symbols()
    print(f"  {len(symbols)} constituents")

    print("Fetching market caps (this takes a couple of minutes)...")
    caps: dict[str, float] = {}
    failed = []
    for i, sym in enumerate(symbols, 1):
        mc = market_cap(sym)
        if mc:
            caps[sym] = mc
        else:
            failed.append(sym)
        if i % 50 == 0:
            print(f"  {i}/{len(symbols)}")
        time.sleep(0.05)  # be polite

    sp500_total = sum(caps.values())
    print(f"  S&P 500 total market cap: ${sp500_total / 1e12:.2f}T ({len(caps)}/{len(symbols)} constituents; {len(failed)} lookups failed)")

    mag7_caps = {}
    for ticker in MAGNIFICENT_7:
        mc = caps.get(ticker) or market_cap(ticker)
        if mc:
            mag7_caps[ticker] = mc
    mag7_total = sum(mag7_caps.values())

    result = {
        "as_of_date": time.strftime("%Y-%m-%d"),
        "sp500_total_market_cap": sp500_total,
        "sp500_constituents_included": len(caps),
        "sp500_constituents_total": len(symbols),
        "mag7_total_market_cap": mag7_total,
        "mag7_share_pct": (mag7_total / sp500_total * 100) if sp500_total else None,
        "mag7_breakdown": mag7_caps,
    }

    (OUTPUT_DIR / "sp500_stat.json").write_text(json.dumps(result, indent=2))
    print(f"\nMag 7 = {result['mag7_share_pct']:.1f}% of the S&P 500's total market cap")
    print(f"Wrote {OUTPUT_DIR / 'sp500_stat.json'}")


if __name__ == "__main__":
    main()
