<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { DataLine, Bell, Refresh, Warning } from '@element-plus/icons-vue'
import StatCard from '@/components/StatCard.vue'
import Sparkline from '@/components/Sparkline.vue'
import { listStocks, type StockItem } from '@/api/stocks'
import { getTodaySignals, type SignalItem } from '@/api/signals'
import { syncStatus, type SyncStatusResp } from '@/api/data'

const router = useRouter()

const stockCount = ref(0)
const signalCount = ref(0)
const lastUpdate = ref('--')
const alertCount = ref(0)
const sparkData = ref<number[]>([10, 22, 18, 30, 28, 40, 36, 50, 48, 55, 60, 58, 70])
const signals = ref<SignalItem[]>([])
const loading = ref(false)

async function loadAll() {
  loading.value = true
  try {
    // 股票总数
    try {
      const stocks: { total?: number; items?: StockItem[] } = await listStocks({ page: 1, size: 1 })
      stockCount.value = stocks.total ?? stocks.items?.length ?? 0
    } catch {
      stockCount.value = 0
    }
    // 今日信号
    try {
      const s = await getTodaySignals()
      signals.value = s ?? []
      signalCount.value = signals.value.length
      alertCount.value = signals.value.filter((x) => x.type === 'sell').length
    } catch {
      signals.value = []
      signalCount.value = 0
      alertCount.value = 0
    }
    // 同步状态
    try {
      const st: SyncStatusResp = await syncStatus()
      lastUpdate.value = st.last_run || st.status || '--'
    } catch {
      lastUpdate.value = '--'
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

function goKline(s: SignalItem) {
  router.push({ name: 'KLine', params: { symbol: s.symbol } })
}
</script>

<template>
  <div class="dashboard">
    <el-card class="welcome" shadow="never">
      <div>
        <h2>欢迎使用量化投资工具</h2>
        <p>一站式 A 股数据、回测、信号与选股平台</p>
      </div>
    </el-card>

    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard title="股票总数" :value="stockCount" :icon="DataLine" color="#409EFF" change="覆盖 A 股主要标的" />
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard title="今日信号" :value="signalCount" :icon="Bell" color="#67C23A" change="实时更新" />
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard title="上次更新" :value="lastUpdate" :icon="Refresh" color="#E6A23C" />
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard title="预警" :value="alertCount" :icon="Warning" color="#F56C6C" change="卖出信号" />
      </el-col>
    </el-row>

    <el-row :gutter="16" class="stat-row">
      <el-col :md="12">
        <el-card shadow="never">
          <template #header>近期数据趋势</template>
          <Sparkline :data="sparkData" :height="120" color="#409EFF" />
        </el-card>
      </el-col>
      <el-col :md="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-head">
              <span>今日信号</span>
              <el-button text type="primary" @click="router.push('/signals')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="signals" v-loading="loading" size="small" empty-text="暂无信号">
            <el-table-column prop="symbol" label="代码" width="90" />
            <el-table-column prop="name" label="名称" width="100" />
            <el-table-column prop="strategy" label="策略" width="120" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="row.type === 'buy' ? 'success' : 'danger'" size="small">
                  {{ row.type === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="goKline(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.welcome h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}
.welcome p {
  margin: 4px 0 0;
  color: #909399;
}
.stat-row {
  margin-bottom: 0;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
