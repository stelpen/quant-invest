<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getTodaySignals, runSignals, type SignalItem } from '@/api/signals'

const router = useRouter()
const loading = ref(false)
const running = ref(false)
const filter = ref<'all' | 'buy' | 'sell'>('all')
const signals = ref<SignalItem[]>([])

const grouped = computed(() => {
  const m: Record<string, SignalItem[]> = {}
  for (const s of signals.value) {
    if (filter.value !== 'all' && s.type !== filter.value.valueOf()) continue
    const key = s.strategy || '其他'
    if (!m[key]) m[key] = []
    m[key].push(s)
  }
  return m
})

async function load() {
  loading.value = true
  try {
    signals.value = (await getTodaySignals()) ?? []
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
}

async function onRun() {
  running.value = true
  try {
    const r = await runSignals()
    ElMessage.success(r?.message || '已触发信号计算')
    await load()
  } catch {
    // ignored
  } finally {
    running.value = false
  }
}

function goKline(s: SignalItem) {
  router.push({ name: 'KLine', params: { symbol: s.symbol } })
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="head">
        <span class="title">今日信号</span>
        <div class="head-right">
          <el-radio-group v-model="filter" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="buy">买入</el-radio-button>
            <el-radio-button value="sell">卖出</el-radio-button>
          </el-radio-group>
          <el-button :icon="Refresh" :loading="running" type="primary" @click="onRun">手动触发</el-button>
        </div>
      </div>
    </template>

    <div v-loading="loading">
      <el-empty v-if="!Object.keys(grouped).length" description="暂无信号" />
      <div v-for="(items, strategy) in grouped" :key="strategy" class="strategy-block">
        <div class="strategy-title">{{ strategy }} <el-tag size="small">{{ items.length }}</el-tag></div>
        <el-table :data="items" stripe size="small" @row-click="goKline" style="cursor: pointer">
          <el-table-column prop="symbol" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag :type="row.type === 'buy' ? 'success' : 'danger'" size="small">
                {{ row.type === 'buy' ? '买入' : '卖出' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="触发价" width="100" align="right">
            <template #default="{ row }">{{ row.price !== undefined ? Number(row.price).toFixed(2) : '--' }}</template>
          </el-table-column>
          <el-table-column prop="date" label="日期" width="110" />
          <el-table-column prop="reason" label="原因" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.head-right {
  display: flex;
  gap: 12px;
  align-items: center;
}
.title {
  font-size: 16px;
  font-weight: 500;
}
.strategy-block {
  margin-bottom: 16px;
}
.strategy-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
