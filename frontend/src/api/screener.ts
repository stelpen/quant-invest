import http from './index'

export interface ScreenerFilters {
  pe_min?: number
  pe_max?: number
  pb_min?: number
  pb_max?: number
  roe_min?: number
  momentum_20d_min?: number
  momentum_20d_max?: number
  volume_min?: number
  [key: string]: number | undefined
}

export interface ScreenerResultItem {
  symbol: string
  name: string
  industry?: string
  price?: number
  pe?: number
  pb?: number
  roe?: number
  momentum_20d?: number
  volume?: number
  [key: string]: unknown
}

export function runScreen(filters: ScreenerFilters): Promise<{ results: ScreenerResultItem[] }> {
  return http.post('/screener/run', { filters }) as unknown as Promise<{ results: ScreenerResultItem[] }>
}
