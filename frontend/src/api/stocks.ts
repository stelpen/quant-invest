import http from './index'

export interface StockListParams {
  q?: string
  page?: number
  size?: number
}

export interface StockItem {
  symbol: string
  name: string
  industry?: string
  market?: string
  price?: number
  change_pct?: number
  pe?: number
  pb?: number
  [key: string]: unknown
}

export interface StockListResp {
  total: number
  items: StockItem[]
  page: number
  size: number
}

export interface StockDetail extends StockItem {
  description?: string
  [key: string]: unknown
}

export function listStocks(params: StockListParams = {}): Promise<StockListResp> {
  return http.get('/stocks', { params }) as unknown as Promise<StockListResp>
}

export function getStock(symbol: string): Promise<StockDetail> {
  return http.get(`/stocks/${encodeURIComponent(symbol)}`) as unknown as Promise<StockDetail>
}

export function searchStocks(q: string): Promise<StockItem[]> {
  return http.get('/stocks/search', { params: { q } }) as unknown as Promise<StockItem[]>
}
