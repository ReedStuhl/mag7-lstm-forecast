"""Honest backtest: model predictions vs actual closes vs a naive baseline,
in real dollar terms, per horizon day (1..5 trading days ahead)."""
import numpy as np
import torch

from .model import HORIZON
from .train import device


def evaluate_test_set(model, test_examples, scalers, raw_closes):
    """test_examples: list of (x_short, x_medium, x_long, y_scaled,
    anchor_index) from dataset.build_examples. raw_closes: unscaled close
    price array (same index space as the anchors) - used for the naive
    baseline and to report real dollar predictions/actuals instead of
    scaled [0,1] values."""
    model.eval()

    rows = []
    with torch.no_grad():
        for x_short, x_medium, x_long, y_scaled, anchor in test_examples:
            xs = torch.tensor(x_short, dtype=torch.float32).unsqueeze(0).to(device)
            xm = torch.tensor(x_medium, dtype=torch.float32).unsqueeze(0).to(device)
            xl = torch.tensor(x_long, dtype=torch.float32).unsqueeze(0).to(device)
            pred_scaled = model(xs, xm, xl).cpu().numpy()[0]

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


# Minimum blend weight given to the model's own output. With no floor,
# alpha=0 (pure naive) is always available to the grid search and gets
# picked for tickers where the model is genuinely weak - which minimizes
# RMSE but produces a forecast line that's visually indistinguishable from
# naive, which defeats the point of showing a model prediction at all. This
# floor is a deliberate trade: it can make the reported RMSE worse than an
# unfloored blend (or worse than naive outright) on tickers where the model
# is weak, in exchange for the forecast always reflecting real model output.
# That trade-off is disclosed in the UI, not hidden.
ALPHA_FLOOR = 0.75


def find_best_alpha(rows: list[dict], floor: float = ALPHA_FLOOR) -> float:
    """Grid-searches a single blend weight alpha in [floor, 1] such that
    blended = alpha * model_prediction + (1 - alpha) * naive_prediction
    minimizes RMSE across all days combined, on the given rows.

    Call this on VALIDATION rows only, never on test rows. Below floor=0,
    alpha=0 (pure naive) would always be in the grid, guaranteeing the
    blend never loses to naive on the data it's tuned against - with
    floor > 0 that guarantee no longer holds, by design (see ALPHA_FLOOR).
    Whether the chosen alpha holds up on genuinely held-out data is exactly
    what the test-set evaluation is for. One alpha per ticker rather than
    one per horizon day, since a validation set of a few dozen examples is
    too little to trust 5 separately-tuned weights without just fitting
    validation noise.
    """
    predicted = np.array([r["predicted"] for r in rows])
    naive = np.array([r["naive"] for r in rows])
    actual = np.array([r["actual"] for r in rows])

    best_alpha, best_rmse = floor, float("inf")
    for alpha in np.linspace(floor, 1.0, 21):
        blended = alpha * predicted + (1 - alpha) * naive
        rmse = float(np.sqrt(np.mean((blended - actual) ** 2)))
        if rmse < best_rmse:
            best_alpha, best_rmse = float(alpha), rmse
    return best_alpha


def blend_rows(rows: list[dict], alpha: float) -> list[dict]:
    """Replaces each row's 'predicted' with alpha * predicted + (1 - alpha) *
    naive - this is what the site actually reports/serves as 'the model's'
    prediction from here on, not the raw network output alone."""
    blended = []
    for r in rows:
        predicted = np.array(r["predicted"])
        naive = np.array(r["naive"])
        blended_pred = alpha * predicted + (1 - alpha) * naive
        blended.append({**r, "predicted": blended_pred.tolist()})
    return blended
