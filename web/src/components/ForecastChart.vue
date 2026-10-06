<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <div class="flex items-baseline justify-between mb-1">
      <h3 class="text-lg font-semibold">{{ prediction.ticker }} - Recent Accuracy & Current Forecast</h3>
      <span class="text-xs text-gray-500">as of {{ longDate(prediction.as_of_date) }}</span>
    </div>
    <p class="text-sm text-gray-500 mb-4">
      Last week, the model {{ lastWeekVerdict }}. {{ targetWeekLabelCap }}'s forecast points to
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

// The forecasted week is "next week" only in the narrow window between the
// Sunday refresh and the following Monday - once that Monday arrives it's
// "this week" from the viewer's actual current date, even though the data
// itself didn't change. Computed against real time so it's correct no
// matter when someone loads the page, not hardcoded to how it looks right
// after a refresh.
const targetWeekLabel = computed(() => {
  const targetMonday = new Date(props.prediction.target_dates[0] + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return today >= targetMonday ? 'this week' : 'next week'
})
const targetWeekLabelCap = computed(() =>
  targetWeekLabel.value === 'this week' ? 'This week' : 'Next week',
)

function avgAbsError(actual: number[], predicted: number[]): number {
  const total = actual.reduce((sum, a, i) => sum + Math.abs(a - predicted[i]), 0)
  return total / actual.length
}

// A real, computed verdict on how the model actually did last week -
// not a description of the chart, which already shows this visually.
const lastWeekVerdict = computed(() => {
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
// direction and magnitude of the implied move by Friday.
const forecastVerdict = computed(() => {
  const p = props.prediction
  const fridayPred = p.predicted.at(-1)!
  const pct = ((fridayPred - p.last_close) / p.last_close) * 100
  const sign = pct >= 0 ? '+' : ''
  return `a ${sign}${pct.toFixed(1)}% move by Friday (from $${p.last_close.toFixed(2)} to $${fridayPred.toFixed(2)})`
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

const chartLabels = computed(() => [
  ...props.prediction.recent_dates.map(shortDate),
  ...props.prediction.target_dates.map(shortDate),
])

// Predicted and Naive run continuously across all 10 days: recent_predicted
// / recent_naive are what the model and the naive baseline would actually
// have said for last week, re-inferred retroactively from the window that
// existed before it started (see predict_week.py's infer()) - not a
// fabricated connector, a real second inference pass. Actual only exists
// for the 5 days that already happened, so it stops there.
const chartSeries = computed<Series[]>(() => {
  const p = props.prediction
  const gapForFuture: null[] = [null, null, null, null, null]

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
    `Actual closing prices for ${props.prediction.ticker} last week, followed by predicted and naive-baseline prices for ${targetWeekLabel.value}`,
)
</script>
