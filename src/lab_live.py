"""Shared 'what does this already-trained window model say right now'
logic, used by both scripts/train_lab_windows.py (right after training) and
scripts/predict_lab_windows.py (the cheap weekly refresh - no retraining).
Mirrors scripts/predict_week.py's anchor-to-the-most-recent-Friday and
retroactive-previous-week approach, applied to the Lab's window models.
"""
from datetime import timedelta

import numpy as np
import torch

from src.lab_model import SimpleSeqModel


def next_trading_days(start_date, n: int) -> list[str]:
    days = []
    d = start_date
    while len(days) < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:
            days.append(str(d.date()))
    return days


def most_recent_friday_index(dates) -> int:
    for i in range(len(dates) - 1, -1, -1):
        if dates[i].weekday() == 4:
            return i
    raise ValueError("No Friday found in the fetched date range")


def predict_seq(model, x_window: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        xt = torch.tensor(x_window, dtype=torch.float32).unsqueeze(0)
        return model(xt).cpu().numpy()[0]


def live_fields(model: SimpleSeqModel, scalers, df, window: int, horizon: int) -> dict:
    """The 'live' half of a lab_windows.json entry: this week's real forecast
    plus last week's retroactively-inferred one, using data/model artifacts
    that already exist - no training happens here."""
    raw_features = df[["Close", "log_return"]].to_numpy()
    features_scaled = scalers.feature.transform(raw_features)

    friday_idx = most_recent_friday_index(df.index)
    if friday_idx + 1 < window:
        raise ValueError(f"not enough data before the most recent Friday ({friday_idx + 1} rows, need {window})")

    end = friday_idx + 1
    pred_scaled = predict_seq(model, features_scaled[end - window:end])
    pred = scalers.target.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()

    last_date = df.index[friday_idx]
    last_close = float(df["Close"].iloc[friday_idx])
    recent_dates = [str(d.date()) for d in df.index[friday_idx - 4:friday_idx + 1]]
    recent_actual = df["Close"].iloc[friday_idx - 4:friday_idx + 1].tolist()
    target_dates = next_trading_days(last_date, horizon)

    prev_friday_idx = most_recent_friday_index(df.index[:friday_idx])
    if prev_friday_idx + 1 < window:
        raise ValueError(
            f"not enough data before the prior Friday to retroactively infer last week "
            f"({prev_friday_idx + 1} rows, need {window})"
        )
    prev_end = prev_friday_idx + 1
    recent_pred_scaled = predict_seq(model, features_scaled[prev_end - window:prev_end])
    recent_predicted = scalers.target.inverse_transform(recent_pred_scaled.reshape(-1, 1)).ravel()
    prev_close = float(df["Close"].iloc[prev_friday_idx])

    return {
        "as_of_date": str(last_date.date()),
        "last_close": last_close,
        "recent_dates": recent_dates,
        "recent_actual": recent_actual,
        "recent_predicted": recent_predicted.tolist(),
        "recent_naive": [prev_close] * horizon,
        "target_dates": target_dates,
        "predicted": pred.tolist(),
        "naive": [last_close] * horizon,
    }
