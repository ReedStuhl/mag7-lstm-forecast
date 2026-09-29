"""Prediction Lab, part 1: trains 5 different modeling approaches on the
*same* NVDA data, same window (30 days), same 5-day horizon, same
chronological split - so the only thing that differs is the algorithm
itself. Answers "LSTM vs RNN vs KNN vs simpler methods" honestly, with a
real backtest for each, not a description of how they differ in theory.

Offline/occasional, like scripts/train_all.py - not run on a schedule.
Writes data/output/lab_models.json.
"""
import copy
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import fetch_daily_closes, add_features
from src.lab_dataset import prepare_dataset, flatten, WindowDataset, HORIZON
from src.lab_model import SimpleSeqModel
from src.train import device

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models" / "lab"
OUTPUT_DIR = ROOT / "data" / "output"

TICKER = "NVDA"
WINDOW = 30  # one consistent window for a fair algorithm-vs-algorithm comparison
EPOCHS = 100
PATIENCE = 15
BATCH_SIZE = 16


def train_seq_model(cell_type: str, train_ds, val_ds):
    model = SimpleSeqModel(cell_type).to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    best_val, best_state, stale = float("inf"), None, 0
    for _epoch in range(1, EPOCHS + 1):
        model.train()
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()

        model.eval()
        vtotal = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                vtotal += criterion(model(xb), yb).item()
        vloss = vtotal / max(len(val_loader), 1)

        if vloss < best_val:
            best_val, best_state, stale = vloss, copy.deepcopy(model.state_dict()), 0
        else:
            stale += 1
        if stale >= PATIENCE:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


def predict_seq(model, x_window: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        xt = torch.tensor(x_window, dtype=torch.float32).unsqueeze(0).to(device)
        return model(xt).cpu().numpy()[0]


def rmse_by_day(preds: np.ndarray, actual: np.ndarray) -> list[float]:
    return [float(np.sqrt(np.mean((preds[:, h] - actual[:, h]) ** 2))) for h in range(HORIZON)]


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== Prediction Lab: model comparison ({TICKER}, {WINDOW}-day window) ===")
    df = add_features(fetch_daily_closes(TICKER))
    prepared = prepare_dataset(df, WINDOW)
    scalers = prepared["scalers"]
    test_examples = prepared["test"]
    print(f"train/val/test examples: {len(prepared['train'])}/{len(prepared['val'])}/{len(test_examples)}")

    X_test, y_test_scaled = flatten(test_examples)
    actual = scalers.target.inverse_transform(y_test_scaled.reshape(-1, 1)).reshape(y_test_scaled.shape)

    # naive baseline: repeat the last known close (feature index 0 = Close) at
    # the end of each test window, same definition used everywhere else on
    # the site (src/evaluate.py).
    last_closes_scaled = X_test[:, -2]  # last timestep's Close (features are [Close, log_return] per step)
    naive_scaled = np.repeat(last_closes_scaled.reshape(-1, 1), HORIZON, axis=1)
    naive = scalers.target.inverse_transform(naive_scaled.reshape(-1, 1)).reshape(naive_scaled.shape)
    naive_rmse = rmse_by_day(naive, actual)
    print(f"naive rmse by day: {[round(x, 2) for x in naive_rmse]}")

    results = {}

    def record(name, preds):
        results[name] = {
            "rmse_by_day": rmse_by_day(preds, actual),
            "example": {
                "actual": actual[-1].tolist(),
                "predicted": preds[-1].tolist(),
                "naive": naive[-1].tolist(),
            },
        }
        print(f"{name} rmse by day: {[round(x, 2) for x in results[name]['rmse_by_day']]}")

    record("naive", naive)

    # Linear regression on the flattened window
    X_train, y_train_scaled = flatten(prepared["train"])
    linear = LinearRegression().fit(X_train, y_train_scaled)
    linear_preds_scaled = linear.predict(X_test)
    linear_preds = scalers.target.inverse_transform(linear_preds_scaled.reshape(-1, 1)).reshape(linear_preds_scaled.shape)
    record("linear", linear_preds)
    joblib.dump(linear, MODELS_DIR / "linear.pkl")

    # KNN regression on the same flattened window
    knn = KNeighborsRegressor(n_neighbors=5).fit(X_train, y_train_scaled)
    knn_preds_scaled = knn.predict(X_test)
    knn_preds = scalers.target.inverse_transform(knn_preds_scaled.reshape(-1, 1)).reshape(knn_preds_scaled.shape)
    record("knn", knn_preds)
    joblib.dump(knn, MODELS_DIR / "knn.pkl")

    # RNN and LSTM, same architecture except the recurrent cell
    train_ds = WindowDataset(prepared["train"])
    val_ds = WindowDataset(prepared["val"])

    for cell_type in ["rnn", "lstm"]:
        print(f"training {cell_type}...")
        model = train_seq_model(cell_type, train_ds, val_ds)
        preds_scaled = np.array([predict_seq(model, ex[0]) for ex in test_examples])
        preds = scalers.target.inverse_transform(preds_scaled.reshape(-1, 1)).reshape(preds_scaled.shape)
        record(cell_type, preds)
        torch.save(model.state_dict(), MODELS_DIR / f"{cell_type}.pth")

    joblib.dump(scalers, MODELS_DIR / "scalers.pkl")

    out = {
        "ticker": TICKER,
        "window_days": WINDOW,
        "n_test_examples": len(test_examples),
        "naive_rmse_by_day": naive_rmse,
        "trained_at": time.strftime("%Y-%m-%d"),
        "models": results,
    }
    (OUTPUT_DIR / "lab_models.json").write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUTPUT_DIR / 'lab_models.json'}")


if __name__ == "__main__":
    main()
