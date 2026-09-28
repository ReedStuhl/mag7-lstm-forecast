<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold mb-1">{{ ticker }} - how honest is this model, really?</h3>
    <p class="text-sm text-gray-500 mb-1">
      Backtested on {{ metrics.n_test_examples }} held-out weeks the model never trained on,
      compared against a naive "assume no change from the last close" baseline.
    </p>
    <p class="text-xs text-gray-400 mb-4">
      As of the model's last training run ({{ metrics.trained_at }}) - this doesn't update
      weekly the way predictions do, only when the model is retrained.
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

    <div v-if="exampleRow">
      <p class="text-sm font-medium mb-2">
        One example from the backtest ({{ exampleRow.target_dates[0] }} -
        {{ exampleRow.target_dates.at(-1) }}) - actual prices vs. what the model and the naive
        baseline predicted for that week, back when it was still unknown
      </p>
      <LineChart
        :series="[
          { name: 'Actual', values: exampleRow.actual, color: '#16a34a' },
          { name: 'Predicted', values: exampleRow.predicted, color: '#2563eb' },
          { name: 'Naive baseline', values: exampleRow.naive, color: '#9ca3af', dashed: true },
        ]"
        :labels="dayLabels(exampleRow.target_dates)"
        :aria-label="`Actual, predicted, and naive-baseline prices for one backtested week for ${ticker}`"
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

// The most recent test-set example. It's dated and clearly framed as "one
// example from the backtest" (not "current") since the section header
// already sets the "as of last training run" context above.
const exampleRow = computed(() => props.backtest.at(-1))

function dayLabels(dates: string[]): string[] {
  return dates.map((d) => new Date(d + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' }))
}
</script>
