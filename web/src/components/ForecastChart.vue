<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <div class="flex items-baseline justify-between mb-1">
      <h3 class="text-lg font-semibold">{{ prediction.ticker }} - last week vs. next week</h3>
      <span class="text-xs text-gray-500">as of {{ prediction.as_of_date }}</span>
    </div>
    <p class="text-sm text-gray-500 mb-4">
      Left half is what actually happened ({{ prediction.recent_dates[0] }} -
      {{ prediction.recent_dates.at(-1) }}). Right half is the forecast for
      {{ prediction.target_dates[0] }} - {{ prediction.target_dates.at(-1) }}, shown against a
      naive "no change" baseline.
    </p>
    <LineChart :series="chartSeries" :labels="chartLabels" :aria-label="ariaLabel" />
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import LineChart, { type Series } from './LineChart.vue'
import type { WeekPrediction } from '../types'

const props = defineProps<{ prediction: WeekPrediction }>()

function shortDate(d: string): string {
  const [, m, day] = d.split('-')
  return `${Number(m)}/${Number(day)}`
}

const chartLabels = computed(() => [
  ...props.prediction.recent_dates.map(shortDate),
  ...props.prediction.target_dates.map(shortDate),
])

// Predicted/naive include the last actual close as their first point so the
// lines visually connect to where "actual" leaves off, instead of floating
// as a disconnected segment. That connector point is real data (the known
// last close), not a prediction.
const chartSeries = computed<Series[]>(() => {
  const gapFirst5: null[] = [null, null, null, null, null]
  const p = props.prediction

  return [
    {
      name: 'Actual',
      values: [...p.recent_actual, ...gapFirst5],
      color: '#16a34a',
    },
    {
      name: 'Predicted',
      values: [...gapFirst5.slice(1), p.last_close, ...p.predicted],
      color: '#2563eb',
    },
    {
      name: 'Naive baseline',
      values: [...gapFirst5.slice(1), p.last_close, ...p.naive],
      color: '#9ca3af',
      dashed: true,
    },
  ]
})

const ariaLabel = computed(
  () =>
    `Actual closing prices for ${props.prediction.ticker} last week, followed by predicted and naive-baseline prices for next week`,
)
</script>
