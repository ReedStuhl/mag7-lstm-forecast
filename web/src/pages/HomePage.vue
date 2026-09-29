<template>
  <div>
    <header class="max-w-3xl mx-auto px-6 pt-10 pb-6 text-center">
      <h1 class="text-3xl sm:text-4xl font-bold">Magnificent 7 Forecast</h1>
      <p class="mt-3 text-gray-600">
        A small triple-branch LSTM (trained on 5-day, 15-day, and 30-day price windows, then
        blended with a naive baseline) predicts next week's closing prices for each of the
        "Magnificent 7" stocks - and is shown honestly against that same naive baseline, not just
        its own numbers.
      </p>
      <router-link
        to="/lab"
        class="inline-block mt-4 px-4 py-2 text-sm border rounded-lg border-gray-300 hover:border-gray-500 transition"
      >
        🔬 Try the Prediction Lab
      </router-link>
    </header>

    <main class="max-w-3xl mx-auto px-6 pb-16 space-y-8">
      <Sp500StatBanner v-if="sp500Stat" :stat="sp500Stat" />

      <section>
        <TickerSelector :tickers="TICKERS" v-model="selected" />
      </section>

      <section v-if="loading" class="text-center text-sm text-gray-400 py-12">Loading data...</section>

      <template v-else-if="loadError">
        <p class="text-center text-sm text-red-500 py-12">
          Couldn't load prediction data. Try refreshing.
        </p>
      </template>

      <template v-else>
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-semibold">{{ selected }}</h2>
          <LiveQuote :ticker="selected" />
        </div>

        <ForecastChart v-if="currentPrediction" :prediction="currentPrediction" />

        <BacktestSection v-if="currentMetrics" :ticker="selected" :metrics="currentMetrics" />
      </template>
    </main>

    <footer class="max-w-3xl mx-auto px-6 pb-10 text-center text-xs text-gray-400 space-y-1">
      <p>
        Predictions refresh weekly from live market data. Model retraining is a manual step, not
        automatic.
      </p>
      <p>Educational demo only - not financial or investment advice.</p>
    </footer>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import TickerSelector from '../components/TickerSelector.vue'
import ForecastChart from '../components/ForecastChart.vue'
import BacktestSection from '../components/BacktestSection.vue'
import Sp500StatBanner from '../components/Sp500StatBanner.vue'
import LiveQuote from '../components/LiveQuote.vue'
import { TICKERS, type MetricsFile, type PredictionsFile, type Sp500Stat, type Ticker } from '../types'

const selected = ref<Ticker>('NVDA')
const loading = ref(true)
const loadError = ref(false)

const predictions = ref<PredictionsFile | null>(null)
const metrics = ref<MetricsFile | null>(null)
const sp500Stat = ref<Sp500Stat | null>(null)

const currentPrediction = computed(() => predictions.value?.[selected.value] ?? null)
const currentMetrics = computed(() => metrics.value?.[selected.value] ?? null)

onMounted(async () => {
  try {
    const [p, m, s] = await Promise.all([
      fetch('/data/predictions.json').then((r) => r.json()),
      fetch('/data/metrics.json').then((r) => r.json()),
      fetch('/data/sp500_stat.json').then((r) => r.json()),
    ])
    predictions.value = p
    metrics.value = m
    sp500Stat.value = s
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})
</script>
