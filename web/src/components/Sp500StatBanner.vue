<template>
  <div class="rounded-xl bg-gray-900 text-white p-6 text-center">
    <p class="text-4xl font-bold tabular-nums">{{ stat.mag7_share_pct.toFixed(1) }}%</p>
    <p class="mt-2 text-sm opacity-80 max-w-md mx-auto">
      These 7 companies make up about
      <strong>{{ stat.mag7_share_pct.toFixed(0) }}%</strong> of the entire S&P 500's market
      value ({{ formatTrillions(stat.mag7_total_market_cap) }} of
      {{ formatTrillions(stat.sp500_total_market_cap) }}), out of 500+ companies in the index.
    </p>
    <p class="mt-2 text-xs opacity-50">
      As of {{ stat.as_of_date }} - computed from
      {{ stat.sp500_constituents_included }}/{{ stat.sp500_constituents_total }} live constituent
      market caps, refreshed periodically, not tick-by-tick.
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { Sp500Stat } from '../types'

defineProps<{ stat: Sp500Stat }>()

function formatTrillions(v: number): string {
  return `$${(v / 1e12).toFixed(1)}T`
}
</script>
