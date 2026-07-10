import http from './index'

export interface SignalItem {
  id?: number | string
  symbol: string
  name?: string
  strategy: string
  type: 'buy' | 'sell' | string
  price?: number
  date?: string
  reason?: string
  [key: string]: unknown
}

export function getTodaySignals(): Promise<SignalItem[]> {
  return http.get('/signals/today') as unknown as Promise<SignalItem[]>
}

export function runSignals(): Promise<{ count?: number; message?: string; [k: string]: unknown }> {
  return http.post('/signals/run', {}) as unknown as Promise<{ count?: number; message?: string; [k: string]: unknown }>
}

export function testNotify(): Promise<{ ok: boolean; message?: string }> {
  return http.post('/signals/test-notify', {}) as unknown as Promise<{ ok: boolean; message?: string }>
}
