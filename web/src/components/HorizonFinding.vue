<template>
  <div class="border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold mb-1">Does forecasting further out help or hurt?</h3>
    <p class="text-sm text-gray-500 mb-1">
      This isn't a picklist to try - it's a finding from a real experiment that changed the live
      site. We backtested the main model at a 10-trading-day horizon (two Mon-Fri weeks) instead
      of 5, across all 7 tickers, and split the result into the first 5 days versus the second 5.
    </p>
    <p class="text-xs text-gray-400 mb-4">
      As of the model's last training run. Same {{ tickerCount }}-ticker backtest that powers the
      live forecast's honesty check, just re-sliced by day.
    </p>

    <p class="text-sm font-medium mb-2">Tickers beating naive, by day ahead (out of {{ tickerCount }})</p>
    <LineChart
      :series="winsSeries"
      :labels="dayLabels"
      aria-label="Number of tickers where the model beats the naive baseline, by day ahead"
    />

    <p class="text-sm mt-3 text-emerald-600">
      Week one: {{ week1Wins }} of {{ tickerCount * 5 }} ticker/day combinations beat naive. Week
      two: {{ week2Wins }} of {{ tickerCount * 5 }}.
    </p>

    <div class="text-sm text-gray-600 space-y-3 mt-4">
      <p>
        The naive baseline just says "assume no change from today's close" - for every day in the
        horizon, the same number. That's a genuinely strong guess 1 trading day out, where real
        prices rarely move much. But it's a much weaker guess 10 trading days out, where real
        prices have had two full weeks to drift away from that anchor. The model isn't getting
        more accurate in absolute terms the further out it predicts - its own errors grow too -
        naive's errors just grow faster, so the gap between them narrows and, for several
        tickers, flips.
      </p>
      <p>
        AMZN and TSLA are the clearest examples: the model loses to naive on every day of week
        one, then wins on every day of week two. GOOGL wins across the full 10 days. AAPL and
        MSFT don't show this pattern - their models are weak enough that even naive's fading
        advantage isn't enough to close the gap. That's why the live site now forecasts two weeks
        instead of one: not because the model got better, but because the comparison it's making
        gets more informative the further out it looks.
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import LineChart, { type Series } from './LineChart.vue'
import type { MetricsFile } from '../types'

const props = defineProps<{ metrics: MetricsFile }>()

const tickers = computed(() => Object.values(props.metrics))
const tickerCount = computed(() => tickers.value.length)
const dayCount = computed(() => tickers.value[0]?.model_rmse_by_day.length ?? 0)
const dayLabels = computed(() => Array.from({ length: dayCount.value }, (_, i) => `Day ${i + 1}`))

const winsByDay = computed(() =>
  Array.from({ length: dayCount.value }, (_, day) =>
    tickers.value.filter((t) => t.model_rmse_by_day[day] < t.naive_rmse_by_day[day]).length,
  ),
)

const winsSeries = computed<Series[]>(() => [
  { name: 'Tickers beating naive', values: winsByDay.value, color: '#2563eb' },
])

function sumWins(days: number[]): number {
  return days.reduce((sum, day) => sum + winsByDay.value[day], 0)
}

const week1Wins = computed(() => sumWins([0, 1, 2, 3, 4]))
const week2Wins = computed(() => sumWins([5, 6, 7, 8, 9]))
</script>
