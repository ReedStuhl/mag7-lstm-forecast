"""Windowing, scaling, and chronological train/val/test split.

Scalers are fit ONLY on the training slice of the raw series (never on
windowed/duplicated data, which would overweight overlapping windows, and
never on val/test data, which would leak future information into scaling).
"""
from dataclasses import dataclass

import numpy as np
import torch
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import Dataset

from .model import SHORT_WINDOW, LONG_WINDOW, HORIZON

TRAIN_FRAC = 0.70
VAL_FRAC = 0.15  # remaining 0.15 is test


@dataclass
class Scalers:
    feature: MinMaxScaler
    target: MinMaxScaler


def fit_scalers(features: np.ndarray, closes: np.ndarray, train_end: int) -> Scalers:
    feature_scaler = MinMaxScaler().fit(features[:train_end])
    target_scaler = MinMaxScaler().fit(closes[:train_end].reshape(-1, 1))
    return Scalers(feature=feature_scaler, target=target_scaler)


def build_examples(features_scaled: np.ndarray, closes_scaled: np.ndarray):
    """features_scaled: (N, 2) [close, log_return], both already scaled.
    closes_scaled: (N,) scaled close, used as the prediction target.
    Returns lists of (x_short, x_long, y, anchor_index)."""
    n = len(features_scaled)
    examples = []
    for i in range(LONG_WINDOW, n - HORIZON + 1):
        x_long = features_scaled[i - LONG_WINDOW:i]
        x_short = features_scaled[i - SHORT_WINDOW:i]
        y = closes_scaled[i:i + HORIZON]
        examples.append((x_short, x_long, y, i))
    return examples


def chronological_split(examples, n_rows: int):
    train_end = int(n_rows * TRAIN_FRAC)
    val_end = int(n_rows * (TRAIN_FRAC + VAL_FRAC))

    train, val, test = [], [], []
    for ex in examples:
        anchor = ex[3]
        if anchor < train_end:
            train.append(ex)
        elif anchor < val_end:
            val.append(ex)
        else:
            test.append(ex)
    return train, val, test


class WindowDataset(Dataset):
    def __init__(self, examples):
        self.examples = examples

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        x_short, x_long, y, _anchor = self.examples[idx]
        return (
            torch.tensor(x_short, dtype=torch.float32),
            torch.tensor(x_long, dtype=torch.float32),
            torch.tensor(y, dtype=torch.float32),
        )


def prepare_ticker_dataset(df):
    """df must already have 'Close' and 'log_return' columns (see data.add_features)."""
    raw_features = df[["Close", "log_return"]].to_numpy()
    raw_closes = df["Close"].to_numpy()
    n_rows = len(df)

    train_end = int(n_rows * TRAIN_FRAC)
    scalers = fit_scalers(raw_features, raw_closes, train_end)

    features_scaled = scalers.feature.transform(raw_features)
    closes_scaled = scalers.target.transform(raw_closes.reshape(-1, 1)).ravel()

    examples = build_examples(features_scaled, closes_scaled)
    train, val, test = chronological_split(examples, n_rows)

    return {
        "train": WindowDataset(train),
        "val": WindowDataset(val),
        "test": WindowDataset(test),
        "scalers": scalers,
        "dates": df.index,
        "raw_closes": raw_closes,
        "test_examples": test,
    }
