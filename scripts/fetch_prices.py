"""Download 2020 closing prices from Yahoo Finance and write site/data/prices.json.

Run once (needs network access to Yahoo):
    pip install yfinance pandas
    python scripts/fetch_prices.py
"""
import json
import re
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
CONTENT_FILE = ROOT / "site" / "data" / "content.js"
OUTPUT_FILE = ROOT / "site" / "data" / "prices.json"

# Official TASI index if Yahoo serves it, otherwise the iShares MSCI Saudi ETF (KSA, USD) as a proxy
BENCHMARK_CANDIDATES = ["^TASI.SR", "KSA"]
BRENT_SYMBOL = "BZ=F"


def load_content_constant(name):
    src = CONTENT_FILE.read_text(encoding="utf-8")
    match = re.search(rf"const {name} = (.*?);\n", src, re.S)
    return json.loads(match.group(1))


def main():
    stock_syms = [s["symbol"] for sec in load_content_constant("SECTORS") for s in sec["stocks"]]
    listing_dates = load_content_constant("LISTING_DATES")

    # yfinance's end date is exclusive, so 2021-01-01 is needed to include the 2020-12-31 session
    raw = yf.download(stock_syms + BENCHMARK_CANDIDATES + [BRENT_SYMBOL],
                      start="2020-01-01", end="2021-01-01", progress=False, auto_adjust=False)
    if raw.empty:
        raise SystemExit("Yahoo Finance returned no data")
    close = raw["Close"]

    # Keep only Tadawul sessions (Sun-Thu in 2020); Brent and the benchmark are carried forward onto them
    saudi_sessions = close[[s for s in stock_syms if s in close.columns]].notna().any(axis=1)
    filled = close.ffill().loc[saudi_sessions]

    benchmark = next((c for c in BENCHMARK_CANDIDATES if c in filled.columns and filled[c].notna().any()), None)
    if benchmark is None:
        raise SystemExit("No benchmark series available")

    dates = filled.index.strftime("%Y-%m-%d").tolist()

    def series(sym):
        col = filled[sym].bfill() if sym in filled.columns else pd.Series(index=filled.index, dtype=float)
        if sym in listing_dates:
            col = col.where(filled.index >= listing_dates[sym])
        return [None if pd.isna(v) else round(float(v), 4) for v in col]

    data = {
        "dates": dates,
        "benchmark": benchmark,
        "series": {**{s: series(s) for s in stock_syms}, "TASI": series(benchmark), "BRENT": series(BRENT_SYMBOL)},
    }
    missing = [s for s, vals in data["series"].items() if all(v is None for v in vals)]
    OUTPUT_FILE.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(dates)} sessions ({dates[0]} -> {dates[-1]}), benchmark={benchmark} to {OUTPUT_FILE}")
    if missing:
        print("WARNING: no data for", ", ".join(missing))


if __name__ == "__main__":
    main()
