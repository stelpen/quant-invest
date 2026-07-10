import http from './index'

export interface IndicatorRequest {
  symbol: string
  start_date: string
  end_date: string
  indicators: string[]
}

export function calculate(req: IndicatorRequest): Promise<Record<string, unknown>> {
  return http.post('/indicators/calculate', req) as unknown as Promise<Record<string, unknown>>
}
