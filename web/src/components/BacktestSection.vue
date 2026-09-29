<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold mb-1">{{ ticker }} - how honest is this model, really?</h3>
    <p class="text-sm text-gray-500 mb-1">
      Backtested on {{ metrics.n_test_examples }} held-out weeks the model never trained on,
      compared against a naive "assume no change from the last close" baseline.
    </p>
    <p class="text-xs text-gray-400 mb-4">
      As of the model's last training run ({{ metrics.trained_at }}) - this doesn't update
      weekly the way predictions do, only when the model is retrained. Reported predictions are
      already blended with the naive baseline (weight {{ metrics.blend_alpha.toFixed(2) }} model,
      {{ (1 - metrics.blend_alpha).toFixed(2) }} naive, tuned on validation data), not the raw
      model output alone.
    </p>

    <p class="text-sm font-medium mb-2">Average error (RMSE) by day ahead</p>
    <LineChart
      :series="rmseSeries"
      :labels="['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5']"
      :aria-label="`Model versus naive baseline error by day ahead for ${ticker}`"
    />
    <p class="text-sm mt-3" :class="modelWinsOverall ? 'text-emerald-600' : 'text-amber-600'">
      {{ verdict }}
    </p>

    <p class="text-xs text-gray-400 mt-4">
      This is an educational demo, not financial advice. Past accuracy (or inaccuracy) doesn't
      predict future results.
    </p>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import LineChart from './LineChart.vue'
import type { TickerMetrics } from '../types'

const props = defineProps<{
  ticker: string
  metrics: TickerMetrics
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
</script>
