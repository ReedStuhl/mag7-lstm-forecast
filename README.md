# Magnificent 7 Forecast

Repo: `mag7-lstm-forecast` · Live: https://web-gamma-kohl-59.vercel.app

An honest, interactive ML demo. A small dual-branch PyTorch LSTM forecasts next week's
closing prices for the "Magnificent 7" stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA),
and is shown transparently against a naive "assume no change" baseline - including the
weeks where the baseline wins, which in this backtest is most of them. It also surfaces a
live-ish stat on how much of the S&P 500's total market cap these 7 companies make up.

This started life in 2022 as a single-stock Bitcoin price predictor and was rebuilt from
the ground up rather than just given a UI - the original version's README advertised
real-time data and RMSE evaluation that didn't actually exist in the code. This version's
claims are backed by what's actually implemented; see "What this is (and isn't)" below.

## How it works

**Model** (`src/model.py`): two small LSTM branches read the same price series at two
lookback lengths - 10 trading days (short-term momentum) and 30 trading days (~6 weeks)
- and their final hidden states are combined into a single head that predicts the
next 5 trading days' closes in one forward pass (not autoregressively - each day is
predicted directly from the same starting window, so Friday's forecast isn't built on
Thursday's guess).

**Training** (`scripts/train_all.py`): ~1 year of daily data per ticker via `yfinance`,
chronological 70/15/15 train/val/test split (scalers fit on train only, no leakage), early
stopping on validation loss. This is a manual/occasional step, not something that runs on
a schedule - the model doesn't need retraining every week.

**Weekly predictions** (`scripts/predict_week.py`): loads the already-trained model and
runs inference on the latest data. This is the actual "run it on Sunday, get Mon-Fri"
job, and it's the piece meant to run on a schedule (see
`.github/workflows/weekly-refresh.yml`).

**Backtest / honesty check** (baked into `train_all.py`'s evaluation step): every test-set
prediction is compared against what actually happened and against the naive baseline, with
RMSE reported per day-ahead. Across all 7 tickers in the current backtest, the naive
baseline beats the model on every single day - that's the headline finding this demo leads
with, not something it hides.

**S&P 500 concentration stat** (`scripts/sp500_stat.py`): sums live market caps for all
500+ current S&P 500 constituents (pulled from Wikipedia's constituent list, priced via
`yfinance`) rather than relying on a hardcoded figure that would silently go stale.

**Frontend** (`web/`): Vue 3 + Vite + TypeScript + Tailwind, statically hosted. It reads
the JSON files the scripts above produce - there's no backend, no live model inference in
the browser, and no server to keep running. The only genuinely live piece is a small
current-price ticker via Finnhub's free tier (optional - the component simply doesn't
render if `VITE_FINNHUB_API_KEY` isn't set).

## What this is (and isn't)

This is an educational demo of an honest ML evaluation process, not a trading signal. The
model does not reliably beat a naive baseline in the current backtest, and that's reported
front and center in the UI rather than buried. Nothing here is investment advice.

## Running it yourself

```bash
pip install -r requirements.txt
python -m scripts.train_all      # trains all 7 tickers, writes data/output/*.json (slow-ish, one-time/occasional)
python -m scripts.predict_week   # generates next week's predictions from the trained models (fast, the actual weekly job)
python -m scripts.sp500_stat     # refreshes the S&P 500 concentration stat (~2 min, offline)
```

```bash
cd web
npm install
npm run dev   # http://localhost:5173
```
