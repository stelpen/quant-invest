<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import StatCard from '@/components/StatCard.vue'
import EquityChart from '@/components/EquityChart.vue'
import { runBacktest, listStrategies, type BacktestRequest, type BacktestResponse, type StrategyInfo } from '@/api/backtest'

const strategies = ref<StrategyInfo[]>([])
const form = reactive({
  strategy: 'ma_cross',
  symbol: '600000',
  start_date: dayjs().subtract(1, 'year').format('YYYY-MM-DD'),
  end_date: dayjs().format('YYYY-MM-DD'),
  initial_capital: 100000,
  // MA cross 动态参数
  fast_period: 5,
  slow_period: 20,
})

const loading = ref(false)
const result = ref<BacktestResponse | null>(null)

async function loadStrategies() {
  try {
    strategies.value = await listStrategies()
    if (strategies.value.length && !form.strategy) {
      form.strategy = strategies.value[0].name
    }
  } catch {
    strategies.value = [{ name: 'ma_cross', description: '双均线交叉' }]
  }
}

async function onRun() {
  if (!form.symbol) {
    ElMessage.warning('请输入股票代码')
    return
  }
  loading.value = true
  try {
    const req: BacktestRequest = {
      strategy: form.strategy,
      symbol: form.symbol,
      start_date: form.start_date,
      end_date: form.end_date,
      initial_capital: Number(form.initial_capital) || 100000,
      params: { fast_period: form.fast_period, slow_period: form.slow_period },
    }
    result.value = await runBacktest(req)
    ElMessage.success('回测完成')
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
}

function fmtPct(v?: number) {
  if (v === undefined || v === null) return '--'
  return (Number(v) * 100).toFixed(2) + '%'
}
function fmtNum(v?: number, digits = 2) {
  if (v === undefined || v === null) return '--'
  return Number(v).toFixed(digits)
}

onMounted(loadStrategies)
</script>

<template>
  <el-card shadow="never" class="config-card">
    <el-form :model="form" inline label-width="100px">
      <el-form-item label="策略">
        <el-select v-model="form.strategy" style="width: 180px">
          <el-option
            v-for="s in strategies"
            :key="s.name"
            :label="s.description || s.name"
            :value="s.name"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="股票代码">
        <el-input v-model="form.symbol" style="width: 140px" placeholder="如 600000" />
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 150px" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 150px" />
      </el-form-item>
      <el-form-item label="初始资金">
        <el-input-number v-model="form.initial_capital" :min="1000" :step="10000" controls-position="right" style="width: 160px" />
      </el-form-item>

      <template v-if="form.strategy === 'ma_cross'">
        <el-form-item label="快线周期">
          <el-input-number v-model="form.fast_period" :min="2" :max="120" controls-position="right" />
        </el-form-item>
        <el-form-item label="慢线周期">
          <el-input-number v-model="form.slow_period" :min="3" :max="250" controls-position="right" />
        </el-form-item>
      </template>

      <el-form-item>
        <el-button type="primary" :loading="loading" @click="onRun">开始回测</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-row :gutter="16" class="mt" v-if="result">
    <el-col :xs="12" :sm="8" :md="4">
      <StatCard title="总收益" :value="fmtPct(result.metrics.total_return)" color="#409EFF" />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4">
      <StatCard title="年化收益" :value="fmtPct(result.metrics.annual_return)" color="#67C23A" />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4">
      <StatCard title="夏普比率" :value="fmtNum(result.metrics.sharpe)" color="#E6A23C" />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4">
      <StatCard title="最大回撤" :value="fmtPct(result.metrics.max_drawdown)" color="#F56C6C" />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4">
      <StatCard title="胜率" :value="fmtPct(result.metrics.win_rate)" color="#909399" />
    </el-col>
    <el-col :xs="12" :sm="8" :md="4">
      <StatCard title="交易次数" :value="result.trades?.length ?? 0" color="#606266" />
    </el-col>
  </el-row>

  <el-card v-if="result" shadow="never" class="mt">
    <template #header>资金曲线</template>
    <EquityChart
      :dates="result.equity_curve.dates"
      :values="result.equity_curve.values"
      :benchmark="result.equity_curve.benchmark"
    />
  </el-card>

  <el-card v-if="result" shadow="never" class="mt">
    <template #header>交易记录</template>
    <el-table :data="result.trades" stripe size="small" max-height="420">
      <el-table-column prop="date" label="日期" width="120" />
      <el-table-column prop="side" label="方向" width="80">
        <template #default="{ row }">
          <el-tag :type="row.side === 'buy' ? 'success' : 'danger'" size="small">
            {{ row.side === 'buy' ? '买入' : '卖出' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" align="right">
        <template #default="{ row }">{{ row.price !== undefined ? Number(row.price).toFixed(2) : '--' }}</template>
      </el-table-column>
      <el-table-column prop="amount" label="数量" align="right" />
      <el-table-column prop="pnl" label="盈亏" align="right">
        <template #default="{ row }">{{ row.pnl !== undefined ? Number(row.pnl).toFixed(2) : '--' }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.config-card {
  margin-bottom: 16px;
}
.mt {
  margin-top: 16px;
}
</style>
