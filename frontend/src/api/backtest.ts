import http from './index'

export interface BacktestRequest {
  strategy: string
  symbol: string
  start_date: string
  end_date: string
  initial_capital: number
  params?: Record<string, unknown>
}

export interface BacktestMetrics {
  total_return?: number
  annual_return?: number
  sharpe?: number
  max_drawdown?: number
  win_rate?: number
  [key: string]: number | undefined
}

export interface BacktestTrade {
  date?: string
  side?: string
  price?: number
  amount?: number
  pnl?: number
  [key: string]: unknown
}

export interface BacktestResponse {
  metrics: BacktestMetrics
  equity_curve: { dates: string[]; values: number[]; benchmark?: number[] }
  trades: BacktestTrade[]
  [key: string]: unknown
}

export interface StrategyInfo {
  name: string
  description?: string
  params?: Array<{ key: string; label: string; type: string; default?: unknown }>
  [key: string]: unknown
}

export function runBacktest(req: BacktestRequest): Promise<BacktestResponse> {
  return http.post('/backtest/run', req) as unknown as Promise<BacktestResponse>
}

export function listStrategies(): Promise<StrategyInfo[]> {
  return http.get('/backtest/strategies') as unknown as Promise<StrategyInfo[]>
}
