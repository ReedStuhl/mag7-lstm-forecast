<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <div class="flex items-baseline justify-between mb-1">
      <h3 class="text-lg font-semibold">{{ prediction.ticker }} - next week's forecast</h3>
      <span class="text-xs text-gray-500">as of {{ prediction.as_of_date }}</span>
    </div>
    <p class="text-sm text-gray-500 mb-4">
      Last close ${{ prediction.last_close.toFixed(2) }}. Predicted for
      {{ prediction.target_dates[0] }} through {{ prediction.target_dates.at(-1) }}.
    </p>
    <LineChart
      :series="[{ name: 'Predicted', values: prediction.predicted, color: '#2563eb' }]"
      :labels="dayLabels"
      :aria-label="`Predicted closing prices for ${prediction.ticker} for the coming week`"
    />
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import LineChart from './LineChart.vue'
import type { WeekPrediction } from '../types'

const props = defineProps<{ prediction: WeekPrediction }>()

const dayLabels = computed(() =>
  props.prediction.target_dates.map((d) =>
    new Date(d + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'short' }),
  ),
)
</script>
