<template>
  <div v-if="enabled && quote" class="inline-flex items-center gap-2 text-sm">
    <span class="relative flex h-2 w-2">
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
      <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
    </span>
    <span class="font-medium">${{ quote.c.toFixed(2) }}</span>
    <span :class="quote.dp >= 0 ? 'text-emerald-600' : 'text-red-600'">
      {{ quote.dp >= 0 ? '+' : '' }}{{ quote.dp.toFixed(2) }}% today
    </span>
  </div>
  <p v-else-if="enabled && error" class="text-xs text-gray-400">Live quote unavailable right now.</p>
</template>

<script lang="ts" setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{ ticker: string }>()

// Free-tier Finnhub key, exposed client-side by necessity (no server here).
// Its free tier is hard rate-capped, so exposure can't turn into a surprise
// bill - see the README for why. Component quietly no-ops if unset.
const API_KEY = import.meta.env.VITE_FINNHUB_API_KEY as string | undefined
const enabled = Boolean(API_KEY)

interface Quote {
  c: number // current price
  dp: number // percent change today
}

const quote = ref<Quote | null>(null)
const error = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

async function fetchQuote() {
  if (!enabled) return
  try {
    const res = await fetch(
      `https://finnhub.io/api/v1/quote?symbol=${props.ticker}&token=${API_KEY}`,
    )
    if (!res.ok) throw new Error(String(res.status))
    const data = await res.json()
    if (typeof data.c === 'number' && data.c > 0) {
      quote.value = { c: data.c, dp: data.dp }
      error.value = false
    } else {
      throw new Error('empty quote')
    }
  } catch {
    error.value = true
  }
}

watch(() => props.ticker, fetchQuote)

onMounted(() => {
  fetchQuote()
  timer = setInterval(fetchQuote, 60_000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
