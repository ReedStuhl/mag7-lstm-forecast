"""Trains the dual-branch LSTM for every Magnificent 7 ticker, evaluates each
on a held-out chronological test set against a naive baseline, and writes:
  - models/<TICKER>/model.pth + scalers.pkl   (for scripts/predict_week.py)
  - data/output/backtest.json                 (predicted vs actual, for the frontend)
  - data/output/metrics.json                  (RMSE by day, model vs naive)

Run this offline, e.g. `python -m scripts.train_all` from the repo root.
Retraining is a manual/occasional maintenance step, not something that runs
on a schedule - see scripts/predict_week.py for the actual weekly job.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import MAGNIFICENT_7, fetch_daily_closes, add_features
from src.dataset import prepare_ticker_dataset
from src.train import train_model
from src.evaluate import evaluate_test_set

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
OUTPUT_DIR = ROOT / "data" / "output"


def train_ticker(ticker: str) -> dict:
    print(f"\n=== {ticker} ===")
    df = add_features(fetch_daily_closes(ticker))
    print(f"  {len(df)} trading days fetched")

    prepared = prepare_ticker_dataset(df)
    print(f"  train/val/test examples: {len(prepared['train'])}/{len(prepared['val'])}/{len(prepared['test'])}")

    model, train_losses, val_losses = train_model(prepared["train"], prepared["val"])

    result = evaluate_test_set(
        model,
        prepared["test_examples"],
        prepared["scalers"],
        prepared["raw_closes"],
    )
    print(f"  test RMSE by day (model): {[round(x, 2) for x in result['model_rmse_by_day']]}")
    print(f"  test RMSE by day (naive): {[round(x, 2) for x in result['naive_rmse_by_day']]}")

    ticker_dir = MODELS_DIR / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), ticker_dir / "model.pth")
    joblib.dump(prepared["scalers"], ticker_dir / "scalers.pkl")

    dates = prepared["dates"]
    backtest_rows = []
    for row in result["rows"]:
        anchor = row["anchor"]
        target_dates = [str(dates[anchor + h].date()) for h in range(len(row["predicted"]))]
        backtest_rows.append({
            "anchor_date": str(dates[anchor - 1].date()),
            "target_dates": target_dates,
            "predicted": row["predicted"],
            "actual": row["actual"],
            "naive": row["naive"],
        })

    return {
        "ticker": ticker,
        "backtest": backtest_rows,
        "metrics": {
            "model_rmse_by_day": result["model_rmse_by_day"],
            "naive_rmse_by_day": result["naive_rmse_by_day"],
            "n_test_examples": len(result["rows"]),
            "n_train_examples": len(prepared["train"]),
            "final_train_loss": train_losses[-1],
            "final_val_loss": val_losses[-1],
            "trained_at": time.strftime("%Y-%m-%d"),
        },
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    backtest_all = {}
    metrics_all = {}

    for ticker in MAGNIFICENT_7:
        result = train_ticker(ticker)
        backtest_all[ticker] = result["backtest"]
        metrics_all[ticker] = result["metrics"]

    (OUTPUT_DIR / "backtest.json").write_text(json.dumps(backtest_all, indent=2))
    (OUTPUT_DIR / "metrics.json").write_text(json.dumps(metrics_all, indent=2))
    print(f"\nWrote {OUTPUT_DIR / 'backtest.json'} and {OUTPUT_DIR / 'metrics.json'}")


if __name__ == "__main__":
    main()
