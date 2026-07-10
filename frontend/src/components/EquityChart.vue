<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

interface Props {
  dates: string[]
  values: number[]
  benchmark?: number[]
  height?: number
}
const props = withDefaults(defineProps<Props>(), { height: 360 })

const option = computed(() => {
  const series: unknown[] = [
    {
      name: '策略净值',
      type: 'line',
      data: props.values,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#409EFF', width: 2 },
      areaStyle: { color: 'rgba(64,158,255,0.1)' },
    },
  ]
  const legend = ['策略净值']
  if (props.benchmark && props.benchmark.length) {
    series.push({
      name: '基准',
      type: 'line',
      data: props.benchmark,
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#909399', width: 1.5 },
    })
    legend.push('基准')
  }
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: legend, top: 0 },
    grid: { left: 50, right: 30, top: 40, bottom: 50 },
    xAxis: {
      type: 'category',
      data: props.dates,
      boundaryGap: false,
      axisLabel: { formatter: (v: string) => (typeof v === 'string' ? v.slice(0, 10) : v) },
    },
    yAxis: { type: 'value', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18 }],
    series,
  }
})
</script>

<template>
  <div :style="{ width: '100%', height: props.height + 'px' }">
    <v-chart :option="option" autoresize />
  </div>
</template>
