<script setup lang="ts">
interface Props {
  title: string
  value: string | number
  change?: string | number
  icon?: string
  color?: string
}
withDefaults(defineProps<Props>(), { color: '#409EFF' })
</script>

<template>
  <div class="stat-card" :style="{ borderTopColor: color }">
    <div class="stat-header">
      <span class="stat-title">{{ title }}</span>
      <el-icon v-if="icon" :size="20" :color="color">
        <component :is="icon" />
      </el-icon>
    </div>
    <div class="stat-value" :style="{ color }">{{ value }}</div>
    <div v-if="change !== undefined" class="stat-change">{{ change }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  border-top: 3px solid #409eff;
  min-height: 96px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #606266;
  font-size: 13px;
}
.stat-title {
  font-weight: 500;
}
.stat-value {
  font-size: 26px;
  font-weight: 600;
  margin-top: 6px;
  line-height: 1.2;
}
.stat-change {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
