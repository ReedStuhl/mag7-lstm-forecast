"""Shared 'what does this already-trained window model say right now'
logic, used by both scripts/train_lab_windows.py (right after training) and
scripts/predict_lab_windows.py (the cheap weekly refresh - no retraining).
Anchors to the most recent Friday, same convention as scripts/predict_week.py.
"""
from datetime import timedelta

import numpy as np
import torch

from src.lab_model import SimpleSeqModel

HISTORY_DAYS = 60  # longest lookback the Playground's history control offers


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
    """The 'live' half of a lab_windows.json entry: this week's real forecast,
    plus up to HISTORY_DAYS of real price history for context, using
    data/model artifacts that already exist - no training happens here."""
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
    target_dates = next_trading_days(last_date, horizon)

    history_start = max(0, friday_idx - HISTORY_DAYS + 1)
    history_dates = [str(d.date()) for d in df.index[history_start:friday_idx + 1]]
    history_actual = df["Close"].iloc[history_start:friday_idx + 1].tolist()

    return {
        "as_of_date": str(last_date.date()),
        "last_close": last_close,
        "history_dates": history_dates,
        "history_actual": history_actual,
        "target_dates": target_dates,
        "predicted": pred.tolist(),
        "naive": [last_close] * horizon,
    }
