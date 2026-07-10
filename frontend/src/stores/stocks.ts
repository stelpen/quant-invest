import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listStocks, type StockItem, type StockListParams, type StockListResp } from '@/api/stocks'

export const useStocksStore = defineStore('stocks', () => {
  const stocks = ref<StockItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const page = ref(1)
  const size = ref(20)
  const query = ref('')

  async function fetchStocks(params?: StockListParams) {
    loading.value = true
    try {
      const p: StockListParams = {
        q: params?.q ?? query.value,
        page: params?.page ?? page.value,
        size: params?.size ?? size.value,
      }
      const res: StockListResp = await listStocks(p)
      stocks.value = res.items ?? []
      total.value = res.total ?? 0
      page.value = res.page ?? p.page ?? 1
      size.value = res.size ?? p.size ?? 20
    } finally {
      loading.value = false
    }
  }

  return { stocks, total, loading, page, size, query, fetchStocks }
})
