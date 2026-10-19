<template>
  <div id="call" class="readout panel">
    <div class="rangecol">
      <div class="eyebrow">Friday {{ longDate(nextFriday(now.d)) }} close · 68% likely range</div>
      <h1>{{ money(now.lo!) }} <span class="hi"><span class="dash">–</span>{{ money(now.hi!) }}</span></h1>

      <div class="rangebar" aria-hidden="true">
        <div class="track"></div>
        <div class="bandx" :style="{ left: barX(now.lo!), width: `calc(${barX(now.hi!)} - ${barX(now.lo!)})` }"></div>
        <div class="tick" :style="{ left: barX(now.c) }"></div>
        <div class="lbl" :style="{ left: barX(now.c) }">last close {{ money(now.c) }}</div>
      </div>

      <p class="why">
        About <b>±{{ widthPct(now.s!).toFixed(1) }}%</b> from last Friday. VIX {{ vixMove }} from
        <b>{{ prev.v.toFixed(1) }}</b> to <b>{{ now.v.toFixed(1) }}</b> last week, so the range
        {{ now.s! > prev.s! ? 'widened' : 'narrowed' }} from ±{{ widthPct(prev.s!).toFixed(1) }}%.
      </p>

      <div class="lean">
        <span class="k">Direction lean</span>
        <span class="v" :class="leanUp ? 'ok' : 'bad'">{{ leanUp ? '▲ Up' : '▼ Down' }} {{ pct(leanUp ? now.p! : 1 - now.p!) }}</span>
        <span class="small">Close to a coin flip. <a href="#experiment">Why we don't headline it</a></span>
      </div>
    </div>

    <div class="strip">
      <div class="eyebrow">Last 12 weeks · range vs. actual close</div>
      <svg class="chart" :viewBox="`0 0 ${W} ${H}`" role="img" aria-label="Weekly ranges and the closes they were aiming at, last 12 weeks">
        <g class="axis">
          <template v-for="t in yTicks" :key="t">
            <line :x1="M.l" :x2="W - M.r" :y1="Y(t)" :y2="Y(t)" />
            <text :x="M.l - 6" :y="Y(t) + 4" text-anchor="end">${{ Math.round(t) }}</text>
          </template>
          <template v-for="(w, k) in weeks" :key="w.call.d">
            <rect
              :x="X(k) - 9" width="18" :y="Y(w.call.hi!)" :height="Y(w.call.lo!) - Y(w.call.hi!)" rx="3"
              fill="var(--band)" stroke="var(--band-line)" :stroke-dasharray="w.close == null ? '3 2' : undefined"
            />
            <circle v-if="w.close != null" :cx="X(k)" :cy="Y(w.close)" r="4.5" :fill="w.hit ? 'var(--up)' : 'var(--down)'" />
            <text v-else :x="X(k)" :y="Y(w.call.lo!) + 14" text-anchor="middle" style="fill: var(--accent)">now</text>
            <text v-if="k % 3 === 0 || w.close == null" :x="X(k)" :y="H - 6" text-anchor="middle">{{ shortDate(w.target) }}</text>
          </template>
        </g>
      </svg>
      <div class="small">
        Closes landed inside the range in {{ hits }} of the last {{ weeks.length - 1 }} weeks. Green dots landed inside, red outside.
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { longDate, money, nextFriday, pct, shortDate, ticks, widthPct, type Lab } from '../lib/lab'

const props = defineProps<{ lab: Lab }>()
const rows = computed(() => props.lab.rows)
const now = computed(() => rows.value[rows.value.length - 1])
const prev = computed(() => rows.value[rows.value.length - 2])
const leanUp = computed(() => now.value.p! >= 0.5)
const vixMove = computed(() => (now.value.v > prev.value.v ? 'rose' : 'fell'))

// range bar: band plus 35% padding either side
const barX = (v: number) => {
  const pad = (now.value.hi! - now.value.lo!) * 0.35
  const lo = now.value.lo! - pad
  const hi = now.value.hi! + pad
  return ((v - lo) / (hi - lo)) * 100 + '%'
}

// 12 graded weeks plus this week's pending range
const weeks = computed(() => {
  const n = rows.value.length
  return rows.value.slice(n - 13).map((call, k, arr) => {
    const next = k < arr.length - 1 ? arr[k + 1] : null
    return {
      call,
      target: next ? next.d : nextFriday(call.d),
      close: next?.c ?? null,
      hit: next != null && next.c >= call.lo! && next.c <= call.hi!,
    }
  })
})
const hits = computed(() => weeks.value.filter((w) => w.hit).length)

const W = 440
const H = 220
const M = { l: 48, r: 10, t: 10, b: 24 }
const extent = computed(() => {
  const vals = weeks.value.flatMap((w) => [w.call.lo!, w.call.hi!, w.close ?? w.call.c])
  return [Math.min(...vals) * 0.997, Math.max(...vals) * 1.003]
})
const X = (k: number) => M.l + ((k + 0.5) / weeks.value.length) * (W - M.l - M.r)
const Y = (v: number) => {
  const [lo, hi] = extent.value
  return M.t + (1 - (v - lo) / (hi - lo)) * (H - M.t - M.b)
}
const yTicks = computed(() => ticks(extent.value[0], extent.value[1], 4))
</script>

<style scoped>
.readout {
  padding: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 28px;
  scroll-margin-top: 16px;
}

.rangecol,
.strip {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

h1 {
  font-stretch: 112%;
  font-weight: 800;
  font-size: clamp(34px, 4.6vw, 50px);
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

.hi {
  white-space: nowrap;
}

.dash {
  color: var(--muted);
  font-weight: 500;
  padding-inline: 0.15em;
}

.rangebar {
  position: relative;
  height: 58px;
  margin-top: 4px;
}

.track {
  position: absolute;
  left: 0;
  right: 0;
  top: 24px;
  height: 2px;
  background: var(--rule);
}

.bandx {
  position: absolute;
  top: 14px;
  height: 22px;
  background: var(--band);
  border: 1px solid var(--accent);
  border-radius: 4px;
}

.tick {
  position: absolute;
  top: 8px;
  width: 2px;
  height: 34px;
  background: var(--ink);
}

.lbl {
  position: absolute;
  top: 42px;
  transform: translateX(-50%);
  font-family: var(--f-data);
  font-size: 11.5px;
  color: var(--muted);
  white-space: nowrap;
}

.why {
  font-size: 14.5px;
  max-width: 46ch;
  margin: 0;
}

.why b {
  font-family: var(--f-data);
  font-weight: 500;
}

.lean {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  border-top: 1px solid var(--rule);
  padding-top: 12px;
  font-size: 14px;
}

.lean .k {
  font-family: var(--f-data);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.lean .v {
  font-family: var(--f-data);
  font-weight: 500;
}

@media (max-width: 760px) {
  .readout {
    grid-template-columns: 1fr;
  }
}
</style>
