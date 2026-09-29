"""The cheap weekly counterpart to scripts/train_lab_windows.py: loads the
already-trained window models and refreshes only the 'live' forecast
fields (this week's anchor, last week's retroactive prediction) - no
training happens here, same relationship predict_week.py has to
train_all.py. Meant to run on the same weekly schedule as
predict_week.py.

Reads and updates data/output/lab_windows.json in place, leaving
rmse_by_day/naive_rmse_by_day/window_days/trained_at untouched from
whatever the last training run wrote.
"""
import json
import sys
from pathlib import Path

import joblib
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import fetch_daily_closes, add_features
from src.lab_model import SimpleSeqModel
from src.lab_live import live_fields
from src.train import device

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models" / "lab"
OUTPUT_DIR = ROOT / "data" / "output"

TICKER = "NVDA"
WINDOWS = {"short": 10, "medium": 30, "long": 60}


def main():
    path = OUTPUT_DIR / "lab_windows.json"
    out = json.loads(path.read_text())

    df = add_features(fetch_daily_closes(TICKER))

    for label, window in WINDOWS.items():
        print(f"refreshing {label} window ({window} days)...")
        model = SimpleSeqModel("lstm").to(device)
        model.load_state_dict(torch.load(MODELS_DIR / f"window_{label}.pth", map_location=device))
        scalers = joblib.load(MODELS_DIR / f"window_{label}_scalers.pkl")

        out[label].update(live_fields(model, scalers, df, window, horizon=5))

    path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
