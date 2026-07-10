<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

interface Props {
  data: number[]
  height?: number
  color?: string
}
const props = withDefaults(defineProps<Props>(), {
  height: 40,
  color: '#409EFF',
})

const option = computed(() => ({
  grid: { left: 0, right: 0, top: 2, bottom: 2 },
  xAxis: { type: 'category', show: false, data: props.data.map((_, i) => i) },
  yAxis: { type: 'value', show: false, scale: true },
  series: [
    {
      type: 'line',
      data: props.data,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: props.color, width: 1.5 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: props.color + '55' },
            { offset: 1, color: props.color + '00' },
          ],
        },
      },
    },
  ],
  tooltip: { trigger: 'axis', show: false },
}))
</script>

<template>
  <div :style="{ width: '100%', height: props.height + 'px' }">
    <v-chart :option="option" autoresize />
  </div>
</template>
