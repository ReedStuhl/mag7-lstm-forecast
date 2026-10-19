"""Weekly refresh for the SPY Prediction Lab site.

1. Reruns the walk-forward experiment on fresh data (scripts/spy_experiment.py).
2. Appends this week's call to data/ledger.json. The ledger is append-only:
   once a week's call is written it is never recomputed, so the scorecard
   grades what the site actually said at the time. The ledger stores the
   model's outputs (direction probability and range width as a log-return
   sigma), not dollar prices, because yfinance's dividend-adjusted closes
   shift slightly over time - the range is rebuilt from the current
   adjusted close, which keeps grading consistent.
3. Writes web/public/data/lab.json for the frontend.

The first run seeds the ledger with the walk-forward history (marked
"backtest"); the latest week of that first run, and every week after, is
"live". A week the job missed and filled in later is marked "backfilled".

Run: python -m scripts.build_site
"""
import json
from datetime import date
from pathlib import Path

import numpy as np

from scripts.spy_experiment import run_experiment

DIRECTION_MODEL = "boosted_trees"
RANGE_METHOD = "vix_scaled"
ROWS_FROM = "2004-01-01"  # a year of context before the first call, for the replay

LEDGER = Path("data/ledger.json")
SITE = Path("web/public/data/lab.json")


def update_ledger(result):
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {
        "direction_model": DIRECTION_MODEL, "range_method": RANGE_METHOD, "launched": None, "calls": [],
    }
    seeding = not ledger["calls"]
    known = {c["d"] for c in ledger["calls"]}
    p = result["predictions"][DIRECTION_MODEL]
    s = result["sigmas"][RANGE_METHOD]
    weeks = [d for d in p.dropna().index if not np.isnan(s.loc[d])]
    latest = weeks[-1]
    for d in weeks:
        key = str(d.date())
        if key in known:
            continue
        if d == latest:
            source = "live"
            ledger["launched"] = ledger["launched"] or key
        else:
            source = "backtest" if seeding else "backfilled"
        ledger["calls"].append({"d": key, "p": round(float(p.loc[d]), 4), "s": round(float(s.loc[d]), 5), "source": source})
    ledger["calls"].sort(key=lambda c: c["d"])
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=1))
    return ledger


def write_site(result, ledger):
    f = result["features"]
    calls = {c["d"]: c for c in ledger["calls"]}
    rows = []
    for d, r in f.loc[ROWS_FROM:].iterrows():
        key = str(d.date())
        row = {"d": key, "c": round(float(r["close"]), 2), "v": round(float(r["vix"]) * 100, 2)}
        if key in calls:
            row["p"], row["s"] = calls[key]["p"], calls[key]["s"]
            if calls[key]["source"] != "backtest":
                row["src"] = calls[key]["source"]
        rows.append(row)
    SITE.parent.mkdir(parents=True, exist_ok=True)
    SITE.write_text(json.dumps({
        "updated": date.today().isoformat(),
        "launched": ledger["launched"],
        "direction_model": ledger["direction_model"],
        "range_method": ledger["range_method"],
        "rows": rows,
        "experiment": result["summary"],
    }, separators=(",", ":")))


def main():
    result = run_experiment(verbose=False)
    ledger = update_ledger(result)
    write_site(result, ledger)
    last = ledger["calls"][-1]
    print(f"ledger: {len(ledger['calls'])} calls, latest {last['d']} ({last['source']}); wrote {SITE}")


if __name__ == "__main__":
    main()
