# SPY Prediction Lab

Repo: `mag7-lstm-forecast` · Live: https://magnificent-forecast.vercel.app

A weekly SPY forecast that shows its work. Every weekend it publishes a likely range for
Friday's close, grades last week's range against what happened, and keeps a public record
that never gets rewritten. It also lets you replay past crashes week by week, and reports
an experiment where four models, including an LSTM, try and fail to beat "always up" at
calling next week's direction.

This repo used to be a Magnificent 7 forecast (and before that, a 2022 Bitcoin LSTM). That
version's weekly forecasts were nearly the same shape every week, because the model had
learned one fixed 5-day pattern and pinned it to the last close. This rebuild narrows to one
instrument with 30+ years of data and predicts things that can actually be checked.

## What the site shows

**This week's range.** A 68% likely range for Friday's close, from VIX: the options
market's own estimate of near-term volatility. VIX usually overstates how much the market
actually moves, so it's scaled down each January to the size that would have caught 68% of
earlier weeks. The range widens when VIX jumps and narrows when it's calm.

**Direction lean.** Up or down with a probability, from a boosted-trees model. It's shown
small on purpose: see the experiment below.

**Scorecard.** Every call is graded on two things: did Friday's close land in the range, and
did SPY move the way the lean said. The lean is always graded next to "always up", because
SPY rises in most weeks and raw accuracy flatters any model that leans up.

**Replay.** Pick a period (2008, 2011, 2018 Q4, 2020, 2022, or the last 6 months) and step
through it one week at a time, seeing only what was known that Friday.

## The experiment (`scripts/spy_experiment.py`)

Weekly SPY since 1994, plus VIX and 10-year and 3-month Treasury yields (`src/spy_data.py`).
Every model is retrained each January on all data before that year, then tested on each week
of that year, from 2005 to now. Nothing is tuned on the test weeks.

Direction models: always up (baseline), logistic regression on price features, logistic
regression with VIX and rates added, boosted trees, and a small LSTM over the last 26 weeks.
None of them beat "always up". Their "down" calls were right less than half the time, and
their probabilities scored no better than quoting the historical up-rate (Brier skill at or
below zero). The site reruns this every week and its summary text follows the numbers, so if
a model ever does pull ahead, the page will say so.

Range methods compared: trailing 52-week volatility, recent-weighted volatility, raw VIX, and
VIX scaled each January. Scaled VIX is the tightest range that still lands near 68%. No method
catches the biggest weekly moves.

## The ledger (`data/ledger.json`)

The scorecard grades what the site actually said, not a recomputed history. `scripts/build_site.py`
appends each week's call to the ledger and never edits earlier ones. Calls before the launch
week are the walk-forward backtest (marked `backtest`); from launch on they're `live`, and a
week the job missed and filled in later is marked `backfilled`.

The ledger stores the model's outputs (direction probability and range width as a log-return
sigma) rather than dollar prices, because Yahoo's dividend-adjusted closes shift slightly
over time. The site rebuilds each range from the current adjusted close, so grading stays
consistent.

## Weekly refresh

`.github/workflows/weekly-refresh.yml` runs `python -m scripts.build_site` every Sunday,
commits `data/ledger.json` and `web/public/data/lab.json`, and Vercel redeploys from main.
The whole run takes under a minute.

## Frontend (`web/`)

Vue 3 + Vite + TypeScript, statically hosted, no backend. It reads one file,
`web/public/data/lab.json`.

## Running it yourself

```bash
pip install -r requirements.txt
python -m scripts.spy_experiment   # full experiment, prints every metric, writes data/output/
python -m scripts.build_site       # this week's call + site data
```

```bash
cd web
npm install
npm run dev        # http://localhost:5173
npm run typecheck
```

Educational project, not financial or investment advice.
