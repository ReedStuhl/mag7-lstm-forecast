"""Honest backtest: model predictions vs actual closes vs a naive baseline,
in real dollar terms, per horizon day (1..5 trading days ahead)."""
import numpy as np
import torch

from .model import HORIZON
from .train import device


def evaluate_test_set(model, test_examples, scalers, raw_closes):
    """test_examples: list of (x_short, x_long, y_scaled, anchor_index) from
    dataset.build_examples. raw_closes: unscaled close price array (same
    index space as the anchors) - used for the naive baseline and to report
    real dollar predictions/actuals instead of scaled [0,1] values."""
    model.eval()

    rows = []
    with torch.no_grad():
        for x_short, x_long, y_scaled, anchor in test_examples:
            xs = torch.tensor(x_short, dtype=torch.float32).unsqueeze(0).to(device)
            xl = torch.tensor(x_long, dtype=torch.float32).unsqueeze(0).to(device)
            pred_scaled = model(xs, xl).cpu().numpy()[0]

            pred = scalers.target.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()
            actual = scalers.target.inverse_transform(y_scaled.reshape(-1, 1)).ravel()
            naive = np.full(HORIZON, raw_closes[anchor - 1])  # persistence baseline

            rows.append({
                "anchor": int(anchor),
                "predicted": pred.tolist(),
                "actual": actual.tolist(),
                "naive": naive.tolist(),
            })

    # RMSE per horizon day (1-indexed: day 1 = next trading day ... day 5)
    model_rmse = []
    naive_rmse = []
    for h in range(HORIZON):
        preds_h = np.array([r["predicted"][h] for r in rows])
        actual_h = np.array([r["actual"][h] for r in rows])
        naive_h = np.array([r["naive"][h] for r in rows])
        model_rmse.append(float(np.sqrt(np.mean((preds_h - actual_h) ** 2))))
        naive_rmse.append(float(np.sqrt(np.mean((naive_h - actual_h) ** 2))))

    return {
        "rows": rows,
        "model_rmse_by_day": model_rmse,
        "naive_rmse_by_day": naive_rmse,
    }
