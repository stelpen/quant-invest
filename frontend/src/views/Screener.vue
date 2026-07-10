<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import { runScreen, type ScreenerFilters, type ScreenerResultItem } from '@/api/screener'

const filters = reactive<ScreenerFilters>({
  pe_min: undefined,
  pe_max: undefined,
  pb_min: undefined,
  pb_max: undefined,
  roe_min: undefined,
  momentum_20d_min: undefined,
  momentum_20d_max: undefined,
  volume_min: undefined,
})
const loading = ref(false)
const results = ref<ScreenerResultItem[]>([])

async function onSubmit() {
  loading.value = true
  try {
    // 过滤掉 undefined 字段
    const payload: ScreenerFilters = {}
    for (const k of Object.keys(filters) as (keyof ScreenerFilters)[]) {
      const v = filters[k]
      if (v !== undefined && v !== null && v !== ('' as unknown as number)) {
        payload[k] = v as number
      }
    }
    const res = await runScreen(payload)
    results.value = res.results ?? []
    ElMessage.success(`共筛出 ${results.value.length} 只股票`)
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
}

function onReset() {
  for (const k of Object.keys(filters) as (keyof ScreenerFilters)[]) {
    ;(filters[k] as number | undefined) = undefined
  }
  results.value = []
}

function onExport() {
  if (!results.value.length) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  const headers = ['代码', '名称', '行业', '价格', 'PE', 'PB', 'ROE', '20日动量', '成交量']
  const rows = results.value.map((r) => [
    r.symbol,
    r.name,
    r.industry ?? '',
    r.price ?? '',
    r.pe ?? '',
    r.pb ?? '',
    r.roe ?? '',
    r.momentum_20d ?? '',
    r.volume ?? '',
  ])
  const csv = [headers, ...rows]
    .map((row) => row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
    .join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `screener_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <el-card shadow="never">
    <template #header>选股条件</template>
    <el-form :model="filters" inline label-width="90px">
      <el-form-item label="PE 最小">
        <el-input-number v-model="filters.pe_min" :min="0" placeholder="如 0" controls-position="right" />
      </el-form-item>
      <el-form-item label="PE 最大">
        <el-input-number v-model="filters.pe_max" :min="0" placeholder="如 30" controls-position="right" />
      </el-form-item>
      <el-form-item label="PB 最小">
        <el-input-number v-model="filters.pb_min" :min="0" :step="0.1" controls-position="right" />
      </el-form-item>
      <el-form-item label="PB 最大">
        <el-input-number v-model="filters.pb_max" :min="0" :step="0.1" controls-position="right" />
      </el-form-item>
      <el-form-item label="ROE 最小(%)">
        <el-input-number v-model="filters.roe_min" :min="0" :step="0.1" controls-position="right" />
      </el-form-item>
      <el-form-item label="20日动量 最小">
        <el-input-number v-model="filters.momentum_20d_min" :step="0.1" controls-position="right" />
      </el-form-item>
      <el-form-item label="20日动量 最大">
        <el-input-number v-model="filters.momentum_20d_max" :step="0.1" controls-position="right" />
      </el-form-item>
      <el-form-item label="成交量 最小">
        <el-input-number v-model="filters.volume_min" :min="0" controls-position="right" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" :loading="loading" @click="onSubmit">开始筛选</el-button>
        <el-button @click="onReset">重置</el-button>
        <el-button :icon="Download" @click="onExport">导出 CSV</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card shadow="never" class="mt">
    <el-table v-loading="loading" :data="results" stripe empty-text="请设置筛选条件后点击“开始筛选”">
      <el-table-column prop="symbol" label="代码" width="100" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="industry" label="行业" min-width="140" show-overflow-tooltip />
      <el-table-column prop="price" label="价格" width="100" align="right">
        <template #default="{ row }">{{ row.price !== undefined ? Number(row.price).toFixed(2) : '--' }}</template>
      </el-table-column>
      <el-table-column prop="pe" label="PE" width="80" align="right" />
      <el-table-column prop="pb" label="PB" width="80" align="right" />
      <el-table-column prop="roe" label="ROE%" width="80" align="right">
        <template #default="{ row }">{{ row.roe !== undefined ? Number(row.roe).toFixed(2) : '--' }}</template>
      </el-table-column>
      <el-table-column label="20日动量" width="110" align="right">
        <template #default="{ row }">
          {{ row.momentum_20d !== undefined ? Number(row.momentum_20d).toFixed(2) + '%' : '--' }}
        </template>
      </el-table-column>
      <el-table-column prop="volume" label="成交量" min-width="120" align="right">
        <template #default="{ row }">{{ row.volume !== undefined ? Number(row.volume).toLocaleString() : '--' }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.mt {
  margin-top: 16px;
}
</style>
