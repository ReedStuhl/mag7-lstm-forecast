<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold mb-1">Naive vs. Linear vs. KNN vs. RNN vs. LSTM</h3>
    <p class="text-sm text-gray-500 mb-1">
      Five different approaches, same {{ data.ticker }} data, same {{ data.window_days }}-day window,
      same 5-day horizon, same held-out test set ({{ data.n_test_examples }} examples). Only the
      algorithm changes - this is a real, backtested comparison, not a description of how they
      differ in theory.
    </p>
    <p class="text-xs text-gray-400 mb-4">
      As of the last training run ({{ data.trained_at }}) - this is a backtest, so it doesn't
      update weekly the way live forecasts do, only when these models are retrained.
    </p>

    <div class="flex flex-wrap gap-2 mb-5" role="tablist" aria-label="Choose a model type">
      <button
        v-for="m in LAB_MODEL_TYPES"
        :key="m"
        type="button"
        role="tab"
        :aria-selected="m === selected"
        class="px-3 py-1.5 rounded-lg border text-sm font-medium transition"
        :class="
          m === selected
            ? 'bg-gray-900 text-white border-gray-900'
            : 'border-gray-300 text-gray-700 hover:border-gray-500'
        "
        @click="selected = m"
      >
        {{ labels[m] }}
      </button>
    </div>

    <p class="text-sm font-medium mb-2">RMSE by day ahead</p>
    <LineChart
      :series="rmseSeries"
      :labels="['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5']"
      :aria-label="`${labels[selected]} versus naive baseline error by day ahead`"
    />
    <p class="text-sm mt-2" :class="daysWon >= 3 ? 'text-emerald-600' : 'text-amber-600'">
      {{ verdict }}
    </p>

    <p class="text-sm font-medium mt-6 mb-2">
      One test-set example: actual vs. what {{ labels[selected] }} predicted
    </p>
    <LineChart
      :series="[
        { name: 'Actual', values: current.example.actual, color: '#16a34a' },
        { name: labels[selected], values: current.example.predicted, color: '#2563eb' },
        { name: 'Naive baseline', values: current.example.naive, color: '#9ca3af', dashed: true },
      ]"
      :labels="['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5']"
      :aria-label="`Actual, ${labels[selected]}, and naive-baseline prices for one test example`"
    />
  </div>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import LineChart from './LineChart.vue'
import { LAB_MODEL_TYPES, type LabModelsFile, type LabModelType } from '../types'

const props = defineProps<{ data: LabModelsFile }>()

const labels: Record<LabModelType, string> = {
  naive: 'Naive',
  linear: 'Linear Regression',
  knn: 'KNN',
  rnn: 'RNN',
  lstm: 'LSTM',
}

const selected = ref<LabModelType>('lstm')

const current = computed(() => props.data.models[selected.value])

const rmseSeries = computed(() => [
  { name: labels[selected.value], values: current.value.rmse_by_day, color: '#2563eb' },
  { name: 'Naive baseline', values: props.data.naive_rmse_by_day, color: '#9ca3af', dashed: true },
])

const daysWon = computed(
  () => current.value.rmse_by_day.filter((v, i) => v < props.data.naive_rmse_by_day[i]).length,
)

const verdict = computed(() => {
  if (selected.value === 'naive') return 'This is the baseline everything else is measured against.'
  const n = daysWon.value
  if (n === 0) return `${labels[selected.value]} didn't beat the naive baseline on any of the 5 days.`
  if (n === 5) return `${labels[selected.value]} beat the naive baseline on all 5 days.`
  return `${labels[selected.value]} beat the naive baseline on ${n} of 5 days.`
})
</script>
