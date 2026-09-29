<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <div class="flex items-baseline justify-between mb-1">
      <h3 class="text-lg font-semibold">{{ prediction.ticker }} - Recent Accuracy & Current Forecast</h3>
      <span class="text-xs text-gray-500">as of {{ longDate(prediction.as_of_date) }}</span>
    </div>
    <p class="text-sm text-gray-500 mb-4">
      Over the last {{ prediction.recent_actual.length }} trading days, the model
      {{ lastPeriodVerdict }}. The forecast through {{ lastTargetDateLabel }} points to
      {{ forecastVerdict }}.
    </p>
    <LineChart :series="chartSeries" :labels="chartLabels" :aria-label="ariaLabel" />
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import LineChart, { type Series } from './LineChart.vue'
import type { WeekPrediction } from '../types'

const props = defineProps<{ prediction: WeekPrediction }>()

function avgAbsError(actual: number[], predicted: number[]): number {
  const total = actual.reduce((sum, a, i) => sum + Math.abs(a - predicted[i]), 0)
  return total / actual.length
}

// A real, computed verdict on how the model actually did over the last
// forecast period - not a description of the chart, which already shows
// this visually.
const lastPeriodVerdict = computed(() => {
  const p = props.prediction
  const modelErr = avgAbsError(p.recent_actual, p.recent_predicted)
  const naiveErr = avgAbsError(p.recent_actual, p.recent_naive)
  const modelStr = `$${modelErr.toFixed(2)}`
  const naiveStr = `$${naiveErr.toFixed(2)}`
  if (modelErr < naiveErr) return `was off by ${modelStr} on average - beating the naive baseline's ${naiveStr}`
  if (modelErr > naiveErr) return `missed by ${modelStr} on average - worse than the naive baseline's ${naiveStr}`
  return `missed by ${modelStr} on average, tying the naive baseline`
})

// Plain-language read of what the forecast line is actually saying:
// direction and magnitude of the implied move by the last forecasted day.
const forecastVerdict = computed(() => {
  const p = props.prediction
  const lastPred = p.predicted.at(-1)!
  const pct = ((lastPred - p.last_close) / p.last_close) * 100
  const sign = pct >= 0 ? '+' : ''
  return `a ${sign}${pct.toFixed(1)}% move (from $${p.last_close.toFixed(2)} to $${lastPred.toFixed(2)})`
})

function shortDate(d: string): string {
  const [, m, day] = d.split('-')
  return `${Number(m)}/${Number(day)}`
}

// m/d/yy, e.g. "9/21/26" - used for the header's date and anywhere else a
// year matters; the chart's own axis labels (shortDate) stay bare m/d.
function longDate(d: string): string {
  const [y, m, day] = d.split('-')
  return `${Number(m)}/${Number(day)}/${y.slice(2)}`
}

const lastTargetDateLabel = computed(() => shortDate(props.prediction.target_dates.at(-1)!))

const chartLabels = computed(() => [
  ...props.prediction.recent_dates.map(shortDate),
  ...props.prediction.target_dates.map(shortDate),
])

// Predicted and Naive run continuously across the whole chart:
// recent_predicted / recent_naive are what the model and the naive baseline
// would actually have said for the period that just completed, re-inferred
// retroactively from the window that existed before it started (see
// predict_week.py's infer()) - not a fabricated connector, a real second
// inference pass. Actual only exists for the days that already happened, so
// it stops there.
const chartSeries = computed<Series[]>(() => {
  const p = props.prediction
  const gapForFuture: null[] = Array(p.target_dates.length).fill(null)

  return [
    {
      name: 'Actual',
      values: [...p.recent_actual, ...gapForFuture],
      color: '#16a34a',
    },
    {
      name: 'Predicted',
      values: [...p.recent_predicted, ...p.predicted],
      color: '#2563eb',
    },
    {
      name: 'Naive baseline',
      values: [...p.recent_naive, ...p.naive],
      color: '#9ca3af',
      dashed: true,
    },
  ]
})

const ariaLabel = computed(
  () =>
    `Actual closing prices for ${props.prediction.ticker} over the last ${props.prediction.recent_actual.length} trading days, followed by predicted and naive-baseline prices for the next ${props.prediction.target_dates.length} trading days`,
)
</script>
