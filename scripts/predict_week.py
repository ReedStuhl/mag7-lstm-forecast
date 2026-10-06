"""The actual "run this on Sunday" job: loads each ticker's already-trained
model, pulls the latest data, and predicts the next 10 trading days (two
Mon-Fri weeks).

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
from src.model import TripleBranchLSTM, SHORT_WINDOW, MEDIUM_WINDOW, LONG_WINDOW, HORIZON
from src.train import device

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
OUTPUT_DIR = ROOT / "data" / "output"

# How much just-completed history (and retroactive accuracy) the homepage
# chart shows, independent of HORIZON (10). Deliberately shorter than the
# forecast itself: showing a full HORIZON-length lookback alongside a
# HORIZON-length forecast makes the compact homepage card denser than it
# needs to be, when the "does a longer horizon help" story already lives in
# the Prediction Lab's dedicated write-up (real backtest data, not this
# live/retroactive comparison). The forecast itself still covers all of
# HORIZON - only how much *history* gets charted alongside it shrinks.
RECENT_DAYS = 5

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

    Predictions are always anchored to a Friday close so the HORIZON-day
    output is always a clean upcoming block of full Mon-Fri weeks - not
    just "whatever trading days happen to follow the last row fetched,"
    which floats depending on what day this script happens to run (e.g. a
    Thursday anchor produces Fri, then next Mon-Thu - a real bug this
    replaces, not a style choice).
    """
    for i in range(len(dates) - 1, -1, -1):
        if dates[i].weekday() == 4:  # Friday
            return i
    raise ValueError("No Friday found in the fetched date range")


def infer(model, scalers, features_scaled, anchor_idx: int) -> list[float]:
    """Run the model as if 'now' were the close at anchor_idx, predicting the
    HORIZON trading days after it. Used both for the live forecast (anchor =
    most recent Friday) and, retroactively, for what the model would have
    said one HORIZON-length period before (anchor = HORIZON trading days
    earlier) - same function either way, just a different anchor."""
    end = anchor_idx + 1  # slice end is exclusive; include the anchor day itself
    x_long = features_scaled[end - LONG_WINDOW:end]
    x_medium = features_scaled[end - MEDIUM_WINDOW:end]
    x_short = features_scaled[end - SHORT_WINDOW:end]

    xs = torch.tensor(x_short, dtype=torch.float32).unsqueeze(0).to(device)
    xm = torch.tensor(x_medium, dtype=torch.float32).unsqueeze(0).to(device)
    xl = torch.tensor(x_long, dtype=torch.float32).unsqueeze(0).to(device)

    with torch.no_grad():
        pred_scaled = model(xs, xm, xl).cpu().numpy()[0]
    return scalers.target.inverse_transform(pred_scaled.reshape(-1, 1)).ravel().tolist()


def blend(predicted: list[float], naive: list[float], alpha: float) -> list[float]:
    """Same blend applied at training/backtest time (src/evaluate.py's
    blend_rows) - alpha was tuned on validation data per ticker, so the
    live forecast reflects the same methodology reported in the backtest."""
    return [alpha * p + (1 - alpha) * n for p, n in zip(predicted, naive)]


def predict_ticker(ticker: str) -> dict:
    ticker_dir = MODELS_DIR / ticker
    scalers = joblib.load(ticker_dir / "scalers.pkl")
    alpha = json.loads((ticker_dir / "blend.json").read_text())["alpha"]

    model = TripleBranchLSTM().to(device)
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

    raw_pred = infer(model, scalers, features_scaled, friday_idx)

    last_date = df.index[friday_idx]
    last_close = float(df["Close"].iloc[friday_idx])
    target_dates = next_trading_days(last_date, HORIZON)

    # The RECENT_DAYS period that just completed (real, known outcomes), so
    # the frontend can chart "what actually happened" leading straight into
    # "what's predicted next" on one continuous timeline, using data already
    # fetched above (no extra cost).
    recent_dates = [str(d.date()) for d in df.index[friday_idx - RECENT_DAYS + 1:friday_idx + 1]]
    recent_actual = df["Close"].iloc[friday_idx - RECENT_DAYS + 1:friday_idx + 1].tolist()

    # Naive "no change" baseline for the predicted period, same definition
    # used in the historical backtest (src/evaluate.py) - lets the forecast
    # chart show the model against that baseline for the *upcoming* period
    # too, not just historically.
    naive = [last_close] * HORIZON
    pred = blend(raw_pred, naive, alpha)

    # What the model (and naive baseline) would have said for the PRIOR
    # RECENT_DAYS period, computed retroactively using the window that
    # existed before it started - not stored/replayed from a prior run,
    # just re-inferred now with the same already-trained weights. Lets the
    # chart's "Predicted" and "Naive" lines run continuously across the
    # whole chart instead of only covering the forecasted half. infer()
    # always predicts a full HORIZON ahead, so this only keeps the first
    # RECENT_DAYS of that forecast - the portion that's actually happened
    # since and can be scored against real outcomes.
    prev_anchor_idx = friday_idx - RECENT_DAYS
    if prev_anchor_idx + 1 < LONG_WINDOW:
        raise ValueError(
            f"{ticker}: not enough data before the prior period to retroactively "
            f"infer its prediction ({prev_anchor_idx + 1} rows, need {LONG_WINDOW})"
        )
    raw_recent_predicted = infer(model, scalers, features_scaled, prev_anchor_idx)[:RECENT_DAYS]
    recent_naive = [float(df["Close"].iloc[prev_anchor_idx])] * RECENT_DAYS
    recent_predicted = blend(raw_recent_predicted, recent_naive, alpha)

    return {
        "ticker": ticker,
        "as_of_date": str(last_date.date()),
        "last_close": last_close,
        "recent_dates": recent_dates,
        "recent_actual": recent_actual,
        "recent_predicted": recent_predicted,
        "recent_naive": recent_naive,
        "target_dates": target_dates,
        "predicted": pred,
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
