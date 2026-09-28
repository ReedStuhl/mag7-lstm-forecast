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


def most_recent_friday_index(dates) -> int:
    """Index of the most recent Friday at or before the last fetched date.

    Predictions are always anchored to a Friday close so the 5-day output
    is always a clean upcoming Mon-Fri block - not just "whatever 5 trading
    days happen to follow the last row fetched," which floats depending on
    what day this script happens to run (e.g. a Thursday anchor produces
    Fri, then next Mon-Thu - a real bug this replaces, not a style choice).
    """
    for i in range(len(dates) - 1, -1, -1):
        if dates[i].weekday() == 4:  # Friday
            return i
    raise ValueError("No Friday found in the fetched date range")


def predict_ticker(ticker: str) -> dict:
    ticker_dir = MODELS_DIR / ticker
    scalers = joblib.load(ticker_dir / "scalers.pkl")

    model = DualBranchLSTM().to(device)
    model.load_state_dict(torch.load(ticker_dir / "model.pth", map_location=device))
    model.eval()

    df = add_features(fetch_daily_closes(ticker, period="3mo"))
    friday_idx = most_recent_friday_index(df.index)
    if friday_idx + 1 < LONG_WINDOW:
        raise ValueError(
            f"{ticker}: not enough data before the most recent Friday "
            f"({friday_idx + 1} rows, need {LONG_WINDOW})"
        )

    raw_features = df[["Close", "log_return"]].to_numpy()
    features_scaled = scalers.feature.transform(raw_features)

    end = friday_idx + 1  # slice end is exclusive; include the Friday itself
    x_long = features_scaled[end - LONG_WINDOW:end]
    x_short = features_scaled[end - SHORT_WINDOW:end]

    xs = torch.tensor(x_short, dtype=torch.float32).unsqueeze(0).to(device)
    xl = torch.tensor(x_long, dtype=torch.float32).unsqueeze(0).to(device)

    with torch.no_grad():
        pred_scaled = model(xs, xl).cpu().numpy()[0]
    pred = scalers.target.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()

    last_date = df.index[friday_idx]
    last_close = float(df["Close"].iloc[friday_idx])
    target_dates = next_trading_days(last_date, HORIZON)

    # The week that just completed (real, known outcomes) - same 5 rows the
    # model's input window ends on, so the frontend can chart "what actually
    # happened" leading straight into "what's predicted next" on one
    # continuous timeline, using data already fetched above (no extra cost).
    recent_dates = [str(d.date()) for d in df.index[friday_idx - 4:friday_idx + 1]]
    recent_actual = df["Close"].iloc[friday_idx - 4:friday_idx + 1].tolist()

    # Naive "no change" baseline for the predicted week, same definition
    # used in the historical backtest (src/evaluate.py) - lets the forecast
    # chart show the model against that baseline for the *upcoming* week
    # too, not just historically.
    naive = [last_close] * HORIZON

    return {
        "ticker": ticker,
        "as_of_date": str(last_date.date()),
        "last_close": last_close,
        "recent_dates": recent_dates,
        "recent_actual": recent_actual,
        "target_dates": target_dates,
        "predicted": pred.tolist(),
        "naive": naive,
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
