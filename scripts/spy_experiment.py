"""Step 1 of the SPY Prediction Lab rebuild: can anything beat "always up"?

Walk-forward test of weekly direction models and weekly range methods on SPY.
Every model is retrained once a year on all data before that year, then
predicts each week of the year it hasn't seen. Nothing is tuned on the test
weeks.

Direction is judged against "always up" (SPY rises in most weeks, so raw
accuracy flatters any model that leans up). Besides accuracy we report:
- Brier skill: probability quality vs. always predicting the historical
  up-rate. Above 0 means the confidence numbers carry real information.
- McNemar p-value: is the accuracy difference vs. always-up more than noise?
- How often the model calls "down", and how much its confidence moves.

Range is judged on whether a +/-1 sigma band catches ~68% of next-week closes,
and how wide it has to be to do that (narrower at the same coverage is better).

Run: python -m scripts.spy_experiment
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy.stats import binomtest
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.spy_data import ALL_FEATURES, PRICE_FEATURES, build_features, fetch_weekly

TEST_START = "2005-01-01"
SEQ_LEN = 26
OUT = Path("data/output/spy_experiment.json")

torch.manual_seed(0)
np.random.seed(0)


# ---------- direction models: fit(train_df) -> predict(test_df, full_df) ----------

def sklearn_model(make, features):
    def run(train, test, full):
        sc = StandardScaler().fit(train[features])
        m = make().fit(sc.transform(train[features]), train["next_up"])
        return m.predict_proba(sc.transform(test[features]))[:, 1]
    return run


def always_up(train, test, full):
    return np.full(len(test), train["next_up"].mean())


class SeqLSTM(torch.nn.Module):
    def __init__(self, n_features, hidden=16):
        super().__init__()
        self.lstm = torch.nn.LSTM(n_features, hidden, batch_first=True)
        self.drop = torch.nn.Dropout(0.3)
        self.head = torch.nn.Linear(hidden, 1)

    def forward(self, x):
        _, (h, _) = self.lstm(x)
        return self.head(self.drop(h[-1])).squeeze(-1)


def lstm_model(train, test, full):
    sc = StandardScaler().fit(train[ALL_FEATURES])
    X = sc.transform(full[ALL_FEATURES]).astype(np.float32)
    pos = {d: i for i, d in enumerate(full.index)}

    def windows(df):
        idx = [pos[d] for d in df.index if pos[d] >= SEQ_LEN - 1]
        xs = np.stack([X[i - SEQ_LEN + 1:i + 1] for i in idx])
        return torch.tensor(xs), [full.index[i] for i in idx]

    xtr, dtr = windows(train)
    ytr = torch.tensor(train.loc[dtr, "next_up"].values, dtype=torch.float32)
    cut = int(len(xtr) * 0.85)  # chronological validation slice for early stopping
    model = SeqLSTM(len(ALL_FEATURES))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-3)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    best, best_state, patience = math.inf, None, 0
    for _ in range(80):
        model.train()
        perm = torch.randperm(cut)
        for b in range(0, cut, 64):
            i = perm[b:b + 64]
            opt.zero_grad()
            loss_fn(model(xtr[i]), ytr[i]).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            v = loss_fn(model(xtr[cut:]), ytr[cut:]).item()
        if v < best - 1e-4:
            best, best_state, patience = v, {k: t.clone() for k, t in model.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 10:
                break
    model.load_state_dict(best_state)
    xte, _ = windows(test)
    with torch.no_grad():
        return torch.sigmoid(model(xte)).numpy()


MODELS = {
    "always_up": always_up,
    "logistic_price": sklearn_model(lambda: LogisticRegression(C=0.1, max_iter=1000), PRICE_FEATURES),
    "logistic_context": sklearn_model(lambda: LogisticRegression(C=0.1, max_iter=1000), ALL_FEATURES),
    "boosted_trees": sklearn_model(lambda: HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.03, max_iter=150, min_samples_leaf=60, l2_regularization=1.0, random_state=0),
        ALL_FEATURES),
    "lstm_context": lstm_model,
}


def walk_forward(f, model):
    labeled = f.dropna(subset=["next_up"])
    out = []
    for year in sorted(set(f.index[f.index >= TEST_START].year)):
        train = labeled[labeled.index < f"{year}-01-01"]
        test = f[(f.index.year == year)]  # includes the latest, not-yet-graded week
        out.append(pd.Series(model(train, test, f), index=test.index))
    return pd.concat(out)


def direction_metrics(p, f):
    p = p[f.loc[p.index, "next_up"].notna()]
    y = f.loc[p.index, "next_up"].values
    call = (p.values >= 0.5)
    hit = call == y.astype(bool)
    up_hit = y.astype(bool)
    # Brier baseline: the historical up-rate known at the time (expanding mean).
    base = f["next_up"].expanding().mean().shift(1).loc[p.index].values
    brier = np.mean((p.values - y) ** 2)
    brier_base = np.mean((base - y) ** 2)
    # McNemar exact test on weeks where model and always-up disagree.
    b = int(np.sum(hit & ~up_hit))
    c = int(np.sum(~hit & up_hit))
    mcnemar = binomtest(b, b + c, 0.5).pvalue if b + c else 1.0
    confident = np.abs(p.values - 0.5) >= 0.1
    downs = ~call
    return {
        "weeks": len(p),
        "accuracy": round(float(hit.mean()), 4),
        "always_up_accuracy": round(float(up_hit.mean()), 4),
        "brier_skill": round(float(1 - brier / brier_base), 4),
        "mcnemar_p_vs_always_up": round(float(mcnemar), 4),
        "down_call_share": round(float(downs.mean()), 4),
        "down_call_accuracy": round(float(hit[downs].mean()), 4) if downs.any() else None,
        "confidence_std": round(float(p.std()), 4),
        "confident_weeks": int(confident.sum()),
        "confident_accuracy": round(float(hit[confident].mean()), 4) if confident.any() else None,
    }


# ---------- range methods: sigma of next week's log return ----------

def vix_scaled(f, target=0.68):
    """VIX-implied sigma, shrunk so a +/-1 sigma band caught `target` of past
    weeks. The scale is refit each January on all earlier weeks only - VIX
    usually overstates realized moves, and this corrects for that without
    looking at the year being predicted."""
    raw = f["vix"] / np.sqrt(52)
    labeled = f.dropna(subset=["next_ret"])
    ratio = labeled["next_ret"].abs() / raw.loc[labeled.index]
    scale = pd.Series(np.nan, index=f.index)
    for year in sorted(set(f.index[f.index >= TEST_START].year)):
        k = float(np.quantile(ratio[ratio.index < f"{year}-01-01"], target))
        scale[f.index.year == year] = k
    return raw * scale


def range_methods(f):
    r = f["r1"]
    return {
        "trailing_52w": r.rolling(52).std(),
        "ewma": np.sqrt((r ** 2).ewm(alpha=0.06).mean()),
        "vix_implied": f["vix"] / np.sqrt(52),
        "vix_scaled": vix_scaled(f),
    }


def range_metrics(sigma, f):
    d = f.dropna(subset=["next_ret"])
    d = d[d.index >= TEST_START]
    s = sigma.loc[d.index]
    inside = d["next_ret"].abs() <= s
    big = d["next_ret"].abs() >= d["next_ret"].abs().quantile(0.9)
    yearly = inside.groupby(d.index.year).mean()
    return {
        "coverage": round(float(inside.mean()), 4),
        "avg_half_width_pct": round(float((np.exp(s) - 1).mean() * 100), 3),
        "coverage_in_biggest_10pct_moves": round(float(inside[big].mean()), 4),
        "worst_year_coverage": round(float(yearly.min()), 4),
        "best_year_coverage": round(float(yearly.max()), 4),
    }


def run_experiment(verbose=True):
    """Fetches fresh data and runs every direction model and range method
    walk-forward. Returns the feature frame, per-week outputs and summary
    metrics; scripts/build_site.py reuses this for the weekly refresh."""
    f = build_features(fetch_weekly())
    if verbose:
        print(f"{len(f)} weekly rows, {f.index[0].date()} to {f.index[-1].date()}")

    preds, direction = {}, {}
    for name, model in MODELS.items():
        preds[name] = walk_forward(f, model)
        direction[name] = direction_metrics(preds[name], f)
        halves = {}
        for label, lo, hi in [("2005-2015", "2005", "2015-12-31"), ("2016-now", "2016", "2100")]:
            halves[label] = direction_metrics(preds[name].loc[lo:hi], f)["accuracy"]
        direction[name]["accuracy_by_period"] = halves
        if verbose:
            print(name, direction[name])

    sigmas = range_methods(f)
    ranges = {k: range_metrics(s, f) for k, s in sigmas.items()}
    if verbose:
        for k, v in ranges.items():
            print("range", k, v)

    return {
        "features": f,
        "predictions": pd.DataFrame(preds),
        "sigmas": pd.DataFrame(sigmas),
        "summary": {
            "test_start": TEST_START,
            "last_week": str(f.index[-1].date()),
            "direction": direction,
            "range": ranges,
        },
    }


def main():
    result = run_experiment()
    f = result["features"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result["summary"], indent=2))
    weekly = result["predictions"].copy()
    weekly["vix_scaled_sigma"] = result["sigmas"]["vix_scaled"]
    weekly.join(f[["close", "vix"]], how="right").to_csv(OUT.with_name("spy_experiment_predictions.csv"))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
