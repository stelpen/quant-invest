<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { listStocks, type StockItem } from '@/api/stocks'

const router = useRouter()
const loading = ref(false)
const data = ref<StockItem[]>([])
const total = ref(0)

const query = reactive({ q: '' })
const pagination = reactive({ page: 1, size: 20 })

async function load() {
  loading.value = true
  try {
    const res = await listStocks({ q: query.q, page: pagination.page, size: pagination.size })
    data.value = res.items ?? []
    total.value = res.total ?? 0
  } catch {
    // ignored
  } finally {
    loading.value = false
  }
}

function onSearch() {
  pagination.page = 1
  load()
}

function onPageChange(p: number) {
  pagination.page = p
  load()
}

function onSizeChange(s: number) {
  pagination.size = s
  pagination.page = 1
  load()
}

function rowClick(row: StockItem) {
  router.push({ name: 'KLine', params: { symbol: row.symbol } })
}

onMounted(load)
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="head">
        <span class="title">股票列表</span>
        <div class="head-right">
          <el-input
            v-model="query.q"
            placeholder="代码 / 名称 / 行业"
            clearable
            style="width: 240px"
            :prefix-icon="Search"
            @keyup.enter="onSearch"
            @clear="onSearch"
          />
          <el-button type="primary" :icon="Search" @click="onSearch">搜索</el-button>
        </div>
      </div>
    </template>

    <el-table
      v-loading="loading"
      :data="data"
      stripe
      style="width: 100%"
      @row-click="rowClick"
    >
      <el-table-column prop="symbol" label="代码" width="100" />
      <el-table-column prop="name" label="名称" width="120" />
      <el-table-column prop="industry" label="行业" min-width="140" show-overflow-tooltip />
      <el-table-column prop="price" label="最新价" width="100" align="right">
        <template #default="{ row }">{{ row.price !== undefined ? Number(row.price).toFixed(2) : '--' }}</template>
      </el-table-column>
      <el-table-column label="涨跌幅" width="100" align="right">
        <template #default="{ row }">
          <span :class="Number(row.change_pct) > 0 ? 'up' : Number(row.change_pct) < 0 ? 'down' : ''">
            {{ row.change_pct !== undefined ? Number(row.change_pct).toFixed(2) + '%' : '--' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="pe" label="PE" width="80" align="right" />
      <el-table-column prop="pb" label="PB" width="80" align="right" />
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :page-sizes="[20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="onPageChange"
        @size-change="onSizeChange"
      />
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
  gap: 8px;
}
.title {
  font-size: 16px;
  font-weight: 500;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
:deep(.up) {
  color: #f56c6c;
}
:deep(.down) {
  color: #67c23a;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
