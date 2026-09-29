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

// --- Prediction Lab ---

export const LAB_MODEL_TYPES = ['naive', 'linear', 'knn', 'rnn', 'lstm'] as const
export type LabModelType = (typeof LAB_MODEL_TYPES)[number]

export interface LabModelResult {
  rmse_by_day: number[]
  example: {
    actual: number[]
    predicted: number[]
    naive: number[]
  }
}

export interface LabModelsFile {
  ticker: Ticker
  window_days: number
  n_test_examples: number
  naive_rmse_by_day: number[]
  trained_at: string
  models: Record<LabModelType, LabModelResult>
}

export const LAB_WINDOW_LABELS = ['short', 'medium', 'long'] as const
export type LabWindowLabel = (typeof LAB_WINDOW_LABELS)[number]

export interface LabWindowResult {
  window_days: number
  as_of_date: string
  last_close: number
  recent_dates: string[]
  recent_actual: number[]
  recent_predicted: number[]
  recent_naive: number[]
  target_dates: string[]
  predicted: number[]
  naive: number[]
  rmse_by_day: number[]
  naive_rmse_by_day: number[]
  trained_at: string
}

export type LabWindowsFile = { ticker: Ticker } & Record<LabWindowLabel, LabWindowResult>
