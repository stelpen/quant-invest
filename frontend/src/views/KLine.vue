<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { init, dispose, type Chart, type Indicator } from 'klinecharts'
import { getKLine, syncData, type KLineResponse } from '@/api/data'
import { Refresh } from '@element-plus/icons-vue'

const route = useRoute()

const symbol = ref<string>((route.params.symbol as string) || '600000')
const dateRange = ref<[string, string]>([
  dayjs().subtract(180, 'day').format('YYYY-MM-DD'),
  dayjs().format('YYYY-MM-DD'),
])
const indicatorMap: Record<string, string> = {
  MA: 'MA',
  EMA: 'EMA',
  MACD: 'MACD',
  RSI: 'RSI',
  KDJ: 'KDJ',
  BOLL: 'BOLL',
}
const selectedIndicators = ref<string[]>(['MA'])
const indicatorsRegistered = ref<Record<string, boolean>>({})
const syncLoading = ref(false)
const showTable = ref(true)
const loading = ref(false)
const klineData = ref<KLineResponse | null>(null)

const chartEl = ref<HTMLDivElement | null>(null)
let chart: Chart | null = null
const createdIndicators: string[] = []

function ensureIndicator(name: string) {
  if (!chart) return
  const key = indicatorMap[name]
  if (!key) return
  if (createdIndicators.includes(key)) {
    // 切换可见性
    chart.overrideIndicator({ name: key, visible: !indicatorsRegistered.value[name] })
    indicatorsRegistered.value[name] = !indicatorsRegistered.value[name]
    return
  }
  const ind: Indicator = { name: key, visible: true }
  chart.createIndicator(ind, false)
  createdIndicators.push(key)
  indicatorsRegistered.value[name] = true
}

function removeIndicator(name: string) {
  if (!chart) return
  const key = indicatorMap[name]
  if (!key) return
  if (createdIndicators.includes(key)) {
    chart.removeIndicator(key)
    const idx = createdIndicators.indexOf(key)
    if (idx >= 0) createdIndicators.splice(idx, 1)
  }
  indicatorsRegistered.value[name] = false
}

function onIndicatorChange(name: string, checked: boolean) {
  if (checked) ensureIndicator(name)
  else removeIndicator(name)
}

async function loadKLine() {
  if (!symbol.value) {
    ElMessage.warning('请输入股票代码')
    return
  }
  loading.value = true
  try {
    const res = await getKLine({
      symbol: symbol.value,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      indicators: selectedIndicators.value,
    })
    klineData.value = res
    applyData(res)
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
}

function applyData(res: KLineResponse) {
  if (!chart) return
  const list = res.dates.map((d, i) => ({
    timestamp: dayjs(d).valueOf(),
    open: Number(res.opens[i]),
    high: Number(res.highs[i]),
    low: Number(res.lows[i]),
    close: Number(res.closes[i]),
    volume: Number(res.volumes[i]),
  }))
  chart.applyNewData(list, true)
}

function initChart() {
  if (!chartEl.value) return
  chart = init(chartEl.value)
}

async function onSync() {
  syncLoading.value = true
  try {
    await syncData()
    ElMessage.success('同步任务已提交')
  } catch {
    // ignored
  } finally {
    syncLoading.value = false
  }
}

onMounted(() => {
  initChart()
  loadKLine()
})

watch(
  () => route.params.symbol,
  (v) => {
    if (v && typeof v === 'string') {
      symbol.value = v
      loadKLine()
    }
  },
)

onBeforeUnmount(() => {
  if (chart && chartEl.value) {
    dispose(chartEl.value)
    chart = null
  }
})
</script>

<template>
  <div class="kline-page">
    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="symbol" placeholder="股票代码 如 600000" style="width: 200px" clearable />
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 260px"
        />
        <el-button type="primary" :loading="loading" @click="loadKLine">查询</el-button>
        <el-button :loading="syncLoading" :icon="Refresh" @click="onSync">同步数据</el-button>
        <div class="ind-checks">
          <el-checkbox
            v-for="name in Object.keys(indicatorMap)"
            :key="name"
            :model-value="selectedIndicators.includes(name)"
            @change="(v: boolean) => { if (v) selectedIndicators.push(name); else selectedIndicators = selectedIndicators.filter(x => x !== name); onIndicatorChange(name, !!v); }"
          >
            {{ name }}
          </el-checkbox>
        </div>
      </div>
    </el-card>

    <el-card class="chart-card" shadow="never" v-loading="loading">
      <div ref="chartEl" class="kline-chart" />
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="card-head">
          <span>K 线数据</span>
          <el-button text type="primary" @click="showTable = !showTable">{{ showTable ? '收起' : '展开' }}</el-button>
        </div>
      </template>
      <el-collapse-transition>
        <el-table
          v-if="showTable && klineData"
          :data="klineData.dates.map((d, i) => ({ date: d, open: klineData.opens[i], high: klineData.highs[i], low: klineData.lows[i], close: klineData.closes[i], volume: klineData.volumes[i] }))"
          size="small"
          stripe
          max-height="360"
        >
          <el-table-column prop="date" label="日期" width="120" />
          <el-table-column label="开盘" align="right">
            <template #default="{ row }">{{ Number(row.open).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="最高" align="right">
            <template #default="{ row }">{{ Number(row.high).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="最低" align="right">
            <template #default="{ row }">{{ Number(row.low).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="收盘" align="right">
            <template #default="{ row }">{{ Number(row.close).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="成交量" align="right">
            <template #default="{ row }">{{ Number(row.volume).toLocaleString() }}</template>
          </el-table-column>
        </el-table>
      </el-collapse-transition>
      <el-empty v-if="!klineData" description="暂无数据" />
    </el-card>
  </div>
</template>

<style scoped>
.kline-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ind-checks {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}
.chart-card {
  padding: 0;
}
.kline-chart {
  width: 100%;
  height: 520px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
