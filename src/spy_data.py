"""Weekly SPY dataset for the Prediction Lab rebuild.

Pulls daily SPY (back to its 1993 launch) plus a few market-context series
via yfinance, collapses everything to Friday-close weekly bars, and builds
features that only use information available at that Friday's close. The
target is whether SPY closes higher the following Friday.

Context series and why they're here:
- ^VIX: the market's own forecast of near-term volatility.
- ^TNX / ^IRX: 10-year and 3-month Treasury yields (rates and curve shape).
"""
import numpy as np
import pandas as pd
import yfinance as yf

START = "1993-01-29"
CONTEXT = {"vix": "^VIX", "tnx": "^TNX", "irx": "^IRX"}

PRICE_FEATURES = ["r1", "r4", "r13", "r26", "vol4", "vol13", "ma10_gap", "ma40_gap", "drawdown52", "volume_ratio"]
CONTEXT_FEATURES = ["vix", "vix_chg1", "vix_rel52", "tnx_chg4", "curve"]
ALL_FEATURES = PRICE_FEATURES + CONTEXT_FEATURES


def _download(ticker: str) -> pd.DataFrame:
    df = yf.download(ticker, start=START, interval="1d", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_weekly() -> pd.DataFrame:
    spy = _download("SPY")[["Close", "Volume"]].dropna()
    daily_ret = np.log(spy["Close"]).diff()

    weekly = pd.DataFrame({
        "close": spy["Close"].resample("W-FRI").last(),
        "volume": spy["Volume"].resample("W-FRI").sum(),
        # realized volatility from daily moves inside each week, annualized
        "rv": daily_ret.resample("W-FRI").std() * np.sqrt(252),
    })
    for name, ticker in CONTEXT.items():
        weekly[name] = _download(ticker)["Close"].resample("W-FRI").last()

    # Drop the current, still-open week so every row is a finished Friday close.
    last_daily = spy.index[-1]
    if last_daily.weekday() != 4:
        weekly = weekly[weekly.index < last_daily.normalize()]
    return weekly.dropna(subset=["close"]).ffill()


def build_features(weekly: pd.DataFrame) -> pd.DataFrame:
    w = weekly.copy()
    r = np.log(w["close"]).diff()
    f = pd.DataFrame(index=w.index)
    f["close"] = w["close"]
    f["r1"] = r
    f["r4"] = r.rolling(4).sum()
    f["r13"] = r.rolling(13).sum()
    f["r26"] = r.rolling(26).sum()
    f["vol4"] = r.rolling(4).std()
    f["vol13"] = r.rolling(13).std()
    f["ma10_gap"] = np.log(w["close"] / w["close"].rolling(10).mean())
    f["ma40_gap"] = np.log(w["close"] / w["close"].rolling(40).mean())
    f["drawdown52"] = np.log(w["close"] / w["close"].rolling(52).max())
    f["volume_ratio"] = np.log(w["volume"].rolling(4).mean() / w["volume"].rolling(52).mean())
    f["vix"] = w["vix"] / 100
    f["vix_chg1"] = np.log(w["vix"]).diff()
    f["vix_rel52"] = np.log(w["vix"] / w["vix"].rolling(52).median())
    f["tnx_chg4"] = w["tnx"].diff(4) / 10
    f["curve"] = (w["tnx"] - w["irx"]) / 10

    # Targets (next week) - never used as inputs.
    f["next_close"] = w["close"].shift(-1)
    f["next_ret"] = np.log(f["next_close"] / f["close"])
    f["next_up"] = (f["next_ret"] > 0).astype(float)
    f.loc[f["next_close"].isna(), "next_up"] = np.nan
    return f.dropna(subset=ALL_FEATURES)
