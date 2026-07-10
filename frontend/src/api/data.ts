import http from './index'

export interface KLineRequest {
  symbol: string
  start_date: string
  end_date: string
  indicators?: string[]
}

export interface KLineResponse {
  symbol: string
  dates: string[]
  opens: number[]
  highs: number[]
  lows: number[]
  closes: number[]
  volumes: number[]
  indicators?: Record<string, unknown>[]
}

export interface SyncStatusResp {
  status: string
  last_run?: string
  message?: string
  progress?: number
  [key: string]: unknown
}

export function getKLine(req: KLineRequest): Promise<KLineResponse> {
  return http.post('/data/kline', req) as unknown as Promise<KLineResponse>
}

export function syncData(): Promise<SyncStatusResp> {
  return http.post('/data/sync', {}) as unknown as Promise<SyncStatusResp>
}

export function syncStatus(): Promise<SyncStatusResp> {
  return http.get('/data/sync/status') as unknown as Promise<SyncStatusResp>
}
