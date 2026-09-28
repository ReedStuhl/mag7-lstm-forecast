export const TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'] as const
export type Ticker = (typeof TICKERS)[number]

export interface WeekPrediction {
  ticker: Ticker
  as_of_date: string
  last_close: number
  recent_dates: string[]
  recent_actual: number[]
  recent_predicted: number[]
  recent_naive: number[]
  target_dates: string[]
  predicted: number[]
  naive: number[]
}

export interface BacktestRow {
  anchor_date: string
  target_dates: string[]
  predicted: number[]
  actual: number[]
  naive: number[]
}

export interface TickerMetrics {
  model_rmse_by_day: number[]
  naive_rmse_by_day: number[]
  n_test_examples: number
  n_train_examples: number
  final_train_loss: number
  final_val_loss: number
  trained_at: string
}

export interface Sp500Stat {
  as_of_date: string
  sp500_total_market_cap: number
  sp500_constituents_included: number
  sp500_constituents_total: number
  mag7_total_market_cap: number
  mag7_share_pct: number
  mag7_breakdown: Record<string, number>
}

export type PredictionsFile = Record<Ticker, WeekPrediction>
export type BacktestFile = Record<Ticker, BacktestRow[]>
export type MetricsFile = Record<Ticker, TickerMetrics>
