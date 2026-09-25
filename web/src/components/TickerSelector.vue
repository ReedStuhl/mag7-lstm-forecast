<template>
  <div class="flex flex-wrap gap-2 justify-center" role="tablist" aria-label="Choose a stock">
    <button
      v-for="t in tickers"
      :key="t"
      type="button"
      role="tab"
      :aria-selected="t === modelValue"
      class="px-4 py-2 rounded-lg border text-sm font-medium transition"
      :class="
        t === modelValue
          ? 'bg-gray-900 text-white border-gray-900 dark:bg-white dark:text-gray-900 dark:border-white'
          : 'border-gray-300 text-gray-700 hover:border-gray-500 dark:border-gray-700 dark:text-gray-300 dark:hover:border-gray-500'
      "
      @click="$emit('update:modelValue', t)"
    >
      {{ t }}
    </button>
  </div>
</template>

<script lang="ts" setup>
import type { Ticker } from '../types'

defineProps<{
  tickers: readonly Ticker[]
  modelValue: Ticker
}>()
defineEmits<{ 'update:modelValue': [Ticker] }>()
</script>
