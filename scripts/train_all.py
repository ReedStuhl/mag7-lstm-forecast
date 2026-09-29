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
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import MAGNIFICENT_7, fetch_daily_closes, add_features
from src.dataset import prepare_ticker_dataset
from src.train import train_model
from src.evaluate import evaluate_test_set, find_best_alpha, blend_rows

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

    # Tune the blend weight on validation rows only (never test), then apply
    # that same fixed alpha to the test set below - see src/evaluate.py's
    # find_best_alpha docstring for why.
    val_result = evaluate_test_set(
        model,
        prepared["val_examples"],
        prepared["scalers"],
        prepared["raw_closes"],
    )
    alpha = find_best_alpha(val_result["rows"])
    print(f"  blend alpha (tuned on validation): {alpha:.2f}")

    raw_result = evaluate_test_set(
        model,
        prepared["test_examples"],
        prepared["scalers"],
        prepared["raw_closes"],
    )
    blended_rows = blend_rows(raw_result["rows"], alpha)

    # Recompute RMSE from the blended predictions - this is what's actually
    # reported and served from here on, not the raw network output alone.
    model_rmse = []
    naive_rmse = []
    for h in range(len(blended_rows[0]["predicted"])):
        preds_h = np.array([r["predicted"][h] for r in blended_rows])
        actual_h = np.array([r["actual"][h] for r in blended_rows])
        naive_h = np.array([r["naive"][h] for r in blended_rows])
        model_rmse.append(float(np.sqrt(np.mean((preds_h - actual_h) ** 2))))
        naive_rmse.append(float(np.sqrt(np.mean((naive_h - actual_h) ** 2))))
    print(f"  test RMSE by day (blended model): {[round(x, 2) for x in model_rmse]}")
    print(f"  test RMSE by day (naive): {[round(x, 2) for x in naive_rmse]}")

    ticker_dir = MODELS_DIR / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), ticker_dir / "model.pth")
    joblib.dump(prepared["scalers"], ticker_dir / "scalers.pkl")
    (ticker_dir / "blend.json").write_text(json.dumps({"alpha": alpha}))

    dates = prepared["dates"]
    backtest_rows = []
    for row in blended_rows:
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
            "model_rmse_by_day": model_rmse,
            "naive_rmse_by_day": naive_rmse,
            "n_test_examples": len(blended_rows),
            "n_train_examples": len(prepared["train"]),
            "final_train_loss": train_losses[-1],
            "final_val_loss": val_losses[-1],
            "blend_alpha": alpha,
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
