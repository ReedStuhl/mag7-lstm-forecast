# Magnificent 7 Forecast

Repo: `mag7-lstm-forecast` · Live: https://magnificent-forecast.vercel.app

An honest, interactive ML demo. A small triple-branch PyTorch LSTM forecasts the next two
weeks' closing prices for the "Magnificent 7" stocks (AAPL, MSFT, GOOGL, AMZN, NVDA, META,
TSLA), blended with a naive "assume no change" baseline, and is shown transparently against
that same baseline - including the tickers and days where the baseline still wins, which in
this backtest is most of them. It also surfaces a live-ish stat on how much of the S&P 500's
total market cap these 7 companies make up.

This started life in 2022 as a single-stock Bitcoin price predictor and was rebuilt from
the ground up rather than just given a UI - the original version's README advertised
real-time data and RMSE evaluation that didn't actually exist in the code. This version's
claims are backed by what's actually implemented; see "What this is (and isn't)" below.

## How it works

**Model** (`src/model.py`): three small LSTM branches read the same price series at three
lookback lengths - 5 trading days (short-term momentum), 15 trading days (~3 weeks), and
30 trading days (~6 weeks) - and their final hidden states are combined into a single head
that predicts the next 10 trading days' closes (two Mon-Fri weeks) in one forward pass (not
autoregressively - each day is predicted directly from the same starting window, so the
second week's forecast isn't built on the first week's guess). The 5/15-day pair came from
the Prediction Lab's window-length experiment, which backtested shorter windows closer to
naive than a longer one on real data; the 30-day branch was added back alongside them
rather than in place of them.

**Why 10 days, not 5** (`src/model.py`'s `HORIZON`, and see the Prediction Lab's horizon
write-up): backtesting a 10-day horizon surfaced a real, if counterintuitive, finding - the
naive "assume no change" baseline gets relatively worse the further out you predict, since
real prices drift further from "no change" the longer the window. On this backtest the
blended model's win rate against naive was 7 of 35 in the first 5 days versus 18 of 35 in
the second 5 days - AMZN and TSLA go from losing every day in week one to winning every day
in week two, and GOOGL wins all 10. The model isn't getting more accurate further out in
absolute terms; naive is just getting worse faster, which is exactly why the comparison
matters more at that range, not less.

**Blending with naive** (`src/evaluate.py`): each ticker's raw model output is blended with
the naive baseline, `alpha * model + (1 - alpha) * naive`, where `alpha` is grid-searched
per ticker on validation data only (never on the test set the backtest reports) to minimize
RMSE, subject to a floor of 0.75 - the model always gets at least 75% of the blend weight.
Without that floor, a weak model would get blended down toward pure naive, which minimizes
RMSE but produces a forecast line that's visually indistinguishable from "no change" -
which defeats the point of showing a model prediction at all. The floor was raised from an
earlier 0.6 specifically to push the forecast further from naive; on this backtest that
change happened to *help* the win rate too (see below), but that's not a guarantee - it's a
small validation set, and the floor's purpose is legibility, not accuracy. On tickers where
the model is weak (AAPL, MSFT, META) it makes the reported RMSE noticeably worse than
naive, and that's shown plainly rather than hidden.

**Training** (`scripts/train_all.py`): ~1 year of daily data per ticker via `yfinance`,
chronological 70/15/15 train/val/test split (scalers fit on train only, no leakage), early
stopping on validation loss. This is a manual/occasional step, not something that runs on
a schedule - the model doesn't need retraining every week.

**Weekly predictions** (`scripts/predict_week.py`): loads the already-trained model and
runs inference on the latest data. This is the actual "run it on Sunday, get the next two
Mon-Fri weeks" job, and it's the piece meant to run on a schedule (see
`.github/workflows/weekly-refresh.yml`).

**Backtest / honesty check** (baked into `train_all.py`'s evaluation step): every test-set
prediction (after blending) is compared against what actually happened and against the
naive baseline, with RMSE reported per day-ahead across all 10 days. In the current
backtest the blended model beats naive on 25 of 70 ticker/day combinations - GOOGL wins all
10 days, AMZN and TSLA win all 5 days of the second week (but none of the first), META
picks up 2 late wins, NVDA 1; AAPL wins 2 of 10 and MSFT wins none. That 7/35 (week one) vs
18/35 (week two) split is the point of extending the horizon in the first place - see "Why
10 days, not 5" above. Before any blending or window tuning the model beat naive on 3 of 35
(5-day horizon only); this is the current state after several rounds of tuning, each of
which is reported here rather than only the final number.

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
model does not reliably beat a naive baseline across all 7 tickers in the current backtest
- it does on some (TSLA, GOOGL, AMZN, NVDA), it does distinctly worse on others (AAPL, MSFT,
META) - and that's reported front and center in the UI rather than buried. Nothing here is
investment advice.

## Running it yourself

```bash
pip install -r requirements.txt
python -m scripts.train_all      # trains all 7 tickers, writes data/output/*.json (slow-ish, one-time/occasional)
python -m scripts.predict_week   # generates the next two weeks' predictions from the trained models (fast, the actual weekly job)
python -m scripts.sp500_stat     # refreshes the S&P 500 concentration stat (~2 min, offline)
```

```bash
cd web
npm install
npm run dev   # http://localhost:5173
```
