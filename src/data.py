"""Fetches daily price history for a ticker via yfinance and builds the
two features the model trains on: scaled-later Close and log return.

This only ever runs offline (training / weekly prediction refresh) - never
in a visitor's browser - so yfinance's lack of a browser-friendly CORS story
doesn't matter here.
"""
import numpy as np
import pandas as pd
import yfinance as yf

MAGNIFICENT_7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

TRAINING_PERIOD = "1y"


def fetch_daily_closes(ticker: str, period: str = TRAINING_PERIOD) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Close"]].dropna()
    df.index.name = "Date"
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
    df = df.dropna()
    return df
