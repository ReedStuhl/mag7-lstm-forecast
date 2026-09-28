"""The actual "run this on Sunday" job: loads each ticker's already-trained
model, pulls the latest data, and predicts the next 5 trading days.

Meant to be re-run periodically (e.g. a weekly scheduled GitHub Action) -
it does NOT retrain, only re-runs inference on fresh data against the
existing model weights. Retraining is a separate, manual step
(scripts/train_all.py) since the model doesn't need to be refit every week.

Writes data/output/predictions.json for the frontend.
"""
import json
import sys
from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import MAGNIFICENT_7, fetch_daily_closes, add_features
from src.model import DualBranchLSTM, SHORT_WINDOW, LONG_WINDOW, HORIZON
from src.train import device

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
OUTPUT_DIR = ROOT / "data" / "output"

# Trading days only - skip weekends. Good enough for a demo; doesn't
# account for market holidays, which is a known, acceptable simplification.
def next_trading_days(start_date, n: int) -> list[str]:
    days = []
    d = start_date
    while len(days) < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            days.append(str(d.date()))
    return days


def predict_ticker(ticker: str) -> dict:
    ticker_dir = MODELS_DIR / ticker
    scalers = joblib.load(ticker_dir / "scalers.pkl")

    model = DualBranchLSTM().to(device)
    model.load_state_dict(torch.load(ticker_dir / "model.pth", map_location=device))
    model.eval()

    df = add_features(fetch_daily_closes(ticker, period="3mo"))
    if len(df) < LONG_WINDOW:
        raise ValueError(f"{ticker}: not enough recent data ({len(df)} rows, need {LONG_WINDOW})")

    raw_features = df[["Close", "log_return"]].to_numpy()
    features_scaled = scalers.feature.transform(raw_features)

    x_long = features_scaled[-LONG_WINDOW:]
    x_short = features_scaled[-SHORT_WINDOW:]

    xs = torch.tensor(x_short, dtype=torch.float32).unsqueeze(0).to(device)
    xl = torch.tensor(x_long, dtype=torch.float32).unsqueeze(0).to(device)

    with torch.no_grad():
        pred_scaled = model(xs, xl).cpu().numpy()[0]
    pred = scalers.target.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()

    last_date = df.index[-1]
    last_close = float(df["Close"].iloc[-1])
    target_dates = next_trading_days(last_date, HORIZON)

    return {
        "ticker": ticker,
        "as_of_date": str(last_date.date()),
        "last_close": last_close,
        "target_dates": target_dates,
        "predicted": pred.tolist(),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    predictions = {}
    for ticker in MAGNIFICENT_7:
        print(f"predicting {ticker}...")
        predictions[ticker] = predict_ticker(ticker)

    (OUTPUT_DIR / "predictions.json").write_text(json.dumps(predictions, indent=2))
    print(f"Wrote {OUTPUT_DIR / 'predictions.json'}")


if __name__ == "__main__":
    main()
