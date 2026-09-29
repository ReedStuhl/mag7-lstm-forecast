"""Prediction Lab, part 2: trains the same LSTM architecture at three
different window lengths (short/medium/long) on NVDA, for the real half of
the Prediction Playground - flipping between these is genuine, backtested
data, unlike the playground's sentiment control (which is an explicitly
labeled simulation, computed client-side).

Offline/occasional, like scripts/train_all.py - retraining doesn't need to
happen weekly. The "live" forecast anchor these produce DOES need to stay
current though; that part is refreshed weekly and cheaply, without
retraining, by scripts/predict_lab_windows.py (shared logic in
src/lab_live.py).

Writes data/output/lab_windows.json, keyed by short/medium/long, in the
same shape predictions.json uses per ticker so the frontend can reuse
ForecastChart's continuous actual-then-predicted line logic.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import fetch_daily_closes, add_features
from src.lab_dataset import prepare_dataset, WindowDataset, HORIZON
from src.lab_live import live_fields
from scripts.train_lab_models import train_seq_model, predict_seq, rmse_by_day

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models" / "lab"
OUTPUT_DIR = ROOT / "data" / "output"

TICKER = "NVDA"
WINDOWS = {"short": 10, "medium": 30, "long": 60}


def run_window(label: str, window: int, df) -> dict:
    print(f"=== {label} window ({window} days) ===")
    prepared = prepare_dataset(df, window)
    scalers = prepared["scalers"]
    test_examples = prepared["test"]
    print(f"  train/val/test: {len(prepared['train'])}/{len(prepared['val'])}/{len(test_examples)}")

    train_ds = WindowDataset(prepared["train"])
    val_ds = WindowDataset(prepared["val"])
    model = train_seq_model("lstm", train_ds, val_ds)
    torch.save(model.state_dict(), MODELS_DIR / f"window_{label}.pth")
    joblib.dump(scalers, MODELS_DIR / f"window_{label}_scalers.pkl")

    preds_scaled = np.array([predict_seq(model, ex[0]) for ex in test_examples])
    y_test_scaled = np.array([ex[1] for ex in test_examples])
    preds = scalers.target.inverse_transform(preds_scaled.reshape(-1, 1)).reshape(preds_scaled.shape)
    actual = scalers.target.inverse_transform(y_test_scaled.reshape(-1, 1)).reshape(y_test_scaled.shape)
    last_close_scaled = np.array([ex[0][-1, 0] for ex in test_examples])
    naive_scaled = np.repeat(last_close_scaled.reshape(-1, 1), HORIZON, axis=1)
    naive = scalers.target.inverse_transform(naive_scaled.reshape(-1, 1)).reshape(naive_scaled.shape)
    print(f"  model rmse by day: {[round(x, 2) for x in rmse_by_day(preds, actual)]}")
    print(f"  naive rmse by day: {[round(x, 2) for x in rmse_by_day(naive, actual)]}")

    return {
        "window_days": window,
        "rmse_by_day": rmse_by_day(preds, actual),
        "naive_rmse_by_day": rmse_by_day(naive, actual),
        "trained_at": time.strftime("%Y-%m-%d"),
        **live_fields(model, scalers, df, window, HORIZON),
    }


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = add_features(fetch_daily_closes(TICKER))
    out = {"ticker": TICKER}
    for label, window in WINDOWS.items():
        out[label] = run_window(label, window, df)

    (OUTPUT_DIR / "lab_windows.json").write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUTPUT_DIR / 'lab_windows.json'}")


if __name__ == "__main__":
    main()
