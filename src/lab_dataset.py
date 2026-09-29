"""Single-window dataset helpers for the Prediction Lab (src/lab_model.py,
scripts/train_lab_models.py, scripts/train_lab_windows.py) - separate from
src/dataset.py, which builds the site's main triple-branch (5-day, 15-day,
and 30-day) windows. The Lab needs one consistent window length at a time
so different algorithms can be compared fairly, and different window
lengths compared against each other, so it can't reuse the multi-branch
shape directly.
"""
from dataclasses import dataclass

import numpy as np
import torch
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import Dataset

HORIZON = 5
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15


@dataclass
class Scalers:
    feature: MinMaxScaler
    target: MinMaxScaler


def fit_scalers(features: np.ndarray, closes: np.ndarray, train_end: int) -> Scalers:
    feature_scaler = MinMaxScaler().fit(features[:train_end])
    target_scaler = MinMaxScaler().fit(closes[:train_end].reshape(-1, 1))
    return Scalers(feature=feature_scaler, target=target_scaler)


def build_examples(features_scaled: np.ndarray, closes_scaled: np.ndarray, window: int):
    n = len(features_scaled)
    examples = []
    for i in range(window, n - HORIZON + 1):
        x = features_scaled[i - window:i]
        y = closes_scaled[i:i + HORIZON]
        examples.append((x, y, i))
    return examples


def chronological_split(examples, n_rows: int):
    train_end = int(n_rows * TRAIN_FRAC)
    val_end = int(n_rows * (TRAIN_FRAC + VAL_FRAC))
    train, val, test = [], [], []
    for ex in examples:
        anchor = ex[2]
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
        x, y, _anchor = self.examples[idx]
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)


def prepare_dataset(df, window: int):
    """df must already have 'Close' and 'log_return' columns (src/data.py)."""
    raw_features = df[["Close", "log_return"]].to_numpy()
    raw_closes = df["Close"].to_numpy()
    n_rows = len(df)

    train_end = int(n_rows * TRAIN_FRAC)
    scalers = fit_scalers(raw_features, raw_closes, train_end)

    features_scaled = scalers.feature.transform(raw_features)
    closes_scaled = scalers.target.transform(raw_closes.reshape(-1, 1)).ravel()

    examples = build_examples(features_scaled, closes_scaled, window)
    train, val, test = chronological_split(examples, n_rows)

    return {
        "train": train,
        "val": val,
        "test": test,
        "scalers": scalers,
        "dates": df.index,
        "raw_closes": raw_closes,
    }


def flatten(examples):
    """(window, 2) -> (window*2,) for sklearn's tabular models (Linear/KNN)."""
    X = np.array([ex[0].reshape(-1) for ex in examples])
    y = np.array([ex[1] for ex in examples])
    return X, y
