<template>
  <div class="w-full">
    <svg :viewBox="`0 0 ${width} ${height}`" class="w-full h-auto" role="img" :aria-label="ariaLabel">
      <!-- gridlines -->
      <line
        v-for="(gy, i) in gridLines"
        :key="'g' + i"
        :x1="padding.left"
        :x2="width - padding.right"
        :y1="gy.y"
        :y2="gy.y"
        class="stroke-gray-200"
        stroke-width="1"
      />
      <text
        v-for="(gy, i) in gridLines"
        :key="'gt' + i"
        :x="padding.left - 8"
        :y="gy.y + 4"
        text-anchor="end"
        class="fill-gray-400 text-[10px]"
      >
        {{ gy.label }}
      </text>

      <!-- series -->
      <g v-for="s in series" :key="s.name">
        <polyline
          :points="pointsFor(s.values)"
          fill="none"
          :stroke="s.color"
          :stroke-width="s.width ?? 2"
          :stroke-dasharray="s.dashed ? '5,4' : undefined"
        />
        <template v-if="showMarkers" v-for="(v, i) in s.values" :key="i">
          <circle v-if="v != null" :cx="xFor(i)" :cy="yFor(v)" r="3" :fill="s.color" />
        </template>
      </g>

      <!-- x labels: thinned out when there are a lot of points, so they don't
           overlap into an unreadable smear - the data itself still plots at
           full resolution, this only reduces which tick text gets printed. -->
      <text
        v-for="i in visibleLabelIndexes"
        :key="'x' + i"
        :x="xFor(i)"
        :y="height - 6"
        text-anchor="middle"
        class="fill-gray-500 text-[10px]"
      >
        {{ labels[i] }}
      </text>
    </svg>

    <div class="flex flex-wrap gap-4 mt-2 justify-center text-xs">
      <div v-for="s in series" :key="'legend-' + s.name" class="flex items-center gap-1.5">
        <span
          class="inline-block w-3 h-0.5"
          :style="{ backgroundColor: s.color, opacity: s.dashed ? 0.6 : 1 }"
        ></span>
        <span class="text-gray-600">{{ s.name }}</span>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'

export interface Series {
  name: string
  values: (number | null)[]
  color: string
  dashed?: boolean
  width?: number
}

const props = defineProps<{
  series: Series[]
  labels: string[]
  ariaLabel?: string
}>()

const width = 480
const height = 220
const padding = { top: 16, right: 16, bottom: 24, left: 48 }

const allValues = computed(() =>
  props.series.flatMap((s) => s.values).filter((v): v is number => v != null),
)
const minV = computed(() => Math.min(...allValues.value))
const maxV = computed(() => Math.max(...allValues.value))
const range = computed(() => Math.max(maxV.value - minV.value, 0.01))

function xFor(i: number): number {
  const n = props.labels.length
  const usable = width - padding.left - padding.right
  return n <= 1 ? padding.left : padding.left + (i / (n - 1)) * usable
}

function yFor(v: number): number {
  const usable = height - padding.top - padding.bottom
  const t = (v - minV.value) / range.value
  return height - padding.bottom - t * usable
}

function pointsFor(values: (number | null)[]): string {
  return values
    .map((v, i) => (v == null ? null : `${xFor(i)},${yFor(v)}`))
    .filter((p): p is string => p != null)
    .join(' ')
}

const gridLines = computed(() => {
  const steps = 4
  return Array.from({ length: steps + 1 }, (_, i) => {
    const v = minV.value + (range.value * i) / steps
    return { y: yFor(v), label: `$${v.toFixed(0)}` }
  })
})

// Dense charts (dozens of days of history) get thinned-out x-axis text and
// no per-point markers, so they read as a clean line instead of a smear of
// overlapping labels and dots. Sparser charts (a handful of days) keep both.
const DENSE_THRESHOLD = 16
const MAX_VISIBLE_LABELS = 10

const showMarkers = computed(() => props.labels.length <= DENSE_THRESHOLD)

// Evenly spaced across the full width, including both endpoints - not a
// fixed step with the last label tacked on afterward, which left an
// uneven (often much narrower) final gap whenever n-1 wasn't a multiple
// of the step, crowding the last one or two labels together.
const visibleLabelIndexes = computed(() => {
  const n = props.labels.length
  if (n <= MAX_VISIBLE_LABELS) return Array.from({ length: n }, (_, i) => i)
  return Array.from({ length: MAX_VISIBLE_LABELS }, (_, i) =>
    Math.round((i * (n - 1)) / (MAX_VISIBLE_LABELS - 1)),
  )
})
</script>
