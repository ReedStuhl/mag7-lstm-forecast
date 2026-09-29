<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold mb-1">Prediction Playground</h3>
    <p class="text-sm text-gray-500 mb-5">
      Change what the model is looking at, and watch the forecast move. The window control is
      real: it swaps between actually trained models. The news sentiment control is not.
    </p>

    <div class="mb-4">
      <p class="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">
        Window length (real, swaps trained models)
      </p>
      <div class="flex gap-2">
        <button
          v-for="w in LAB_WINDOW_LABELS"
          :key="w"
          type="button"
          class="px-3 py-1.5 rounded-lg border text-sm font-medium transition"
          :class="
            w === window
              ? 'bg-gray-900 text-white border-gray-900'
              : 'border-gray-300 text-gray-700 hover:border-gray-500'
          "
          @click="window = w"
        >
          {{ windowLabels[w] }} ({{ data[w].window_days }}d)
        </button>
      </div>
    </div>

    <div class="mb-4">
      <p class="text-xs font-medium uppercase tracking-wide text-gray-400 mb-2">
        History shown (real price data, for context)
      </p>
      <div class="flex gap-2">
        <button
          v-for="h in historyOptions"
          :key="h"
          type="button"
          class="px-3 py-1.5 rounded-lg border text-sm font-medium transition"
          :class="
            h === historyDays
              ? 'bg-gray-900 text-white border-gray-900'
              : 'border-gray-300 text-gray-700 hover:border-gray-500'
          "
          @click="historyDays = h"
        >
          {{ h }} days
        </button>
      </div>
    </div>

    <div class="mb-5">
      <p class="text-xs font-medium uppercase tracking-wide text-amber-600 mb-2">
        News sentiment (simulated, not real news data)
      </p>
      <div class="flex gap-2">
        <button
          v-for="s in sentimentOptions"
          :key="s.value"
          type="button"
          class="px-3 py-1.5 rounded-lg border text-sm font-medium transition"
          :class="
            s.value === sentiment
              ? 'bg-amber-100 border-amber-400 text-amber-900'
              : 'border-gray-300 text-gray-700 hover:border-gray-500'
          "
          @click="sentiment = s.value"
        >
          {{ s.label }}
        </button>
      </div>
    </div>

    <div class="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-5 text-xs text-amber-800">
      <strong>This is a simulation, not a real prediction.</strong> There's no news or social data
      behind the sentiment control. It applies a simple, invented rule (a small daily price nudge
      that grows the further into the week you look) so you can feel how weighing an input more
      heavily changes an output. The window control is genuinely real: it's swapping between Long
      Short-Term Memory (LSTM) models actually trained on {{ data[window].window_days }} days of
      price history each.
    </div>

    <LineChart :series="chartSeries" :labels="chartLabels" :aria-label="ariaLabel" />

    <p class="text-xs text-gray-400 mt-3">
      Forecast as of {{ data[window].as_of_date }}, refreshed weekly. RMSE at this window length
      (as of last training run, {{ data[window].trained_at }}):
      {{ data[window].rmse_by_day.map((v) => '$' + v.toFixed(0)).join(', ') }} by day (naive:
      {{ data[window].naive_rmse_by_day.map((v) => '$' + v.toFixed(0)).join(', ') }}).
    </p>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import LineChart, { type Series } from './LineChart.vue'
import { LAB_WINDOW_LABELS, type LabWindowLabel, type LabWindowsFile } from '../types'

const props = defineProps<{ data: LabWindowsFile }>()

const windowLabels: Record<LabWindowLabel, string> = {
  short: 'Short',
  medium: 'Medium',
  long: 'Long',
}

const window = ref<LabWindowLabel>('medium')

const historyOptions = [5, 30, 60] as const
const historyDays = ref<(typeof historyOptions)[number]>(30)

type SentimentLevel = -1 | 0 | 1
const sentiment = ref<SentimentLevel>(0)
const sentimentOptions: { value: SentimentLevel; label: string }[] = [
  { value: -1, label: 'Negative' },
  { value: 0, label: 'Neutral' },
  { value: 1, label: 'Positive' },
]

// Illustrative only: a made-up, clearly-labeled rule, not derived from any
// real sentiment signal. Grows a bit each day to suggest sentiment's effect
// compounding over the week, capped at a small, plausible-looking magnitude
// so it demonstrates direction/weighting without implying real precision.
const DAILY_NUDGE = 0.005 // 0.5% per day of horizon, at full +/-1 sentiment

function applySentiment(predicted: number[], level: SentimentLevel): number[] {
  return predicted.map((v, i) => v * (1 + level * DAILY_NUDGE * (i + 1)))
}

function shortDate(d: string): string {
  const [, m, day] = d.split('-')
  return `${Number(m)}/${Number(day)}`
}

const history = computed(() => {
  const d = props.data[window.value]
  const n = historyDays.value
  return {
    dates: d.history_dates.slice(-n),
    actual: d.history_actual.slice(-n),
  }
})

const chartLabels = computed(() => [
  ...history.value.dates.map(shortDate),
  ...props.data[window.value].target_dates.map(shortDate),
])

// Actual shows real price history (length set by the history control),
// nothing for the forecast period since that hasn't happened yet.
// Predicted and Naive baseline only cover the forecasted 5 days - this is
// the playground's forecast, not a look back at how the model did last
// time (that comparison already lives in the model-comparison section
// above).
const chartSeries = computed<Series[]>(() => {
  const d = props.data[window.value]
  const gap: null[] = Array(historyDays.value).fill(null)
  const adjustedPredicted = applySentiment(d.predicted, sentiment.value)

  return [
    { name: 'Actual', values: [...history.value.actual, ...gap], color: '#16a34a' },
    {
      name: 'Predicted (adjusted)',
      values: [...gap, ...adjustedPredicted],
      color: '#2563eb',
    },
    { name: 'Naive baseline', values: [...gap, ...d.naive], color: '#9ca3af', dashed: true },
  ]
})

const ariaLabel = computed(
  () =>
    `Simulated forecast for the ${window.value} window with ${sentiment.value > 0 ? 'positive' : sentiment.value < 0 ? 'negative' : 'neutral'} sentiment applied`,
)
</script>
