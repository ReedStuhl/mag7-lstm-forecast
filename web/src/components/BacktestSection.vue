<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold mb-1">{{ ticker }} - how honest is this model, really?</h3>
    <p class="text-sm text-gray-500 mb-4">
      Backtested on {{ metrics.n_test_examples }} held-out weeks the model never trained on,
      compared against a naive "assume no change from the last close" baseline.
    </p>

    <div class="mb-6">
      <p class="text-sm font-medium mb-2">Average error (RMSE) by day ahead</p>
      <LineChart
        :series="rmseSeries"
        :labels="['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5']"
        :aria-label="`Model versus naive baseline error by day ahead for ${ticker}`"
      />
      <p class="text-sm mt-3" :class="modelWinsOverall ? 'text-emerald-600' : 'text-amber-600'">
        {{ verdict }}
      </p>
    </div>

    <div v-if="latestRow">
      <p class="text-sm font-medium mb-2">
        Most recent backtest window ({{ latestRow.target_dates[0] }} -
        {{ latestRow.target_dates.at(-1) }})
      </p>
      <LineChart
        :series="[
          { name: 'Predicted', values: latestRow.predicted, color: '#2563eb' },
          { name: 'Actual', values: latestRow.actual, color: '#16a34a' },
          { name: 'Naive baseline', values: latestRow.naive, color: '#9ca3af', dashed: true },
        ]"
        :labels="dayLabels(latestRow.target_dates)"
        :aria-label="`Predicted, actual, and naive-baseline prices for the most recent backtest window for ${ticker}`"
      />
    </div>

    <p class="text-xs text-gray-400 mt-4">
      This is an educational demo, not financial advice. Past accuracy (or inaccuracy) doesn't
      predict future results.
    </p>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import LineChart from './LineChart.vue'
import type { BacktestRow, TickerMetrics } from '../types'

const props = defineProps<{
  ticker: string
  metrics: TickerMetrics
  backtest: BacktestRow[]
}>()

const rmseSeries = computed(() => [
  { name: 'Model', values: props.metrics.model_rmse_by_day, color: '#2563eb' },
  { name: 'Naive baseline', values: props.metrics.naive_rmse_by_day, color: '#9ca3af', dashed: true },
])

const daysModelWins = computed(
  () =>
    props.metrics.model_rmse_by_day.filter(
      (v, i) => v < props.metrics.naive_rmse_by_day[i],
    ).length,
)

const modelWinsOverall = computed(() => daysModelWins.value >= 3)

const verdict = computed(() => {
  const n = daysModelWins.value
  if (n === 0) return `The naive baseline beat the model on every one of the 5 days. Short-term price moves are genuinely hard to predict from price history alone.`
  if (n === 5) return `The model beat the naive baseline on all 5 days in this backtest.`
  return `The model beat the naive baseline on ${n} of 5 days in this backtest.`
})

const latestRow = computed(() => props.backtest.at(-1))

function dayLabels(dates: string[]): string[] {
  return dates.map((d) => new Date(d + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' }))
}
</script>
