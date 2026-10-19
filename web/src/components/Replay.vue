<template>
  <section id="replay" class="section">
    <div>
      <div class="eyebrow">Replay</div>
      <h2>Rewind the market and watch the range hold or break</h2>
      <p class="lede">
        Pick a stretch of history and step forward one week at a time. Each Friday the range is set
        from that day's VIX, then the next week is revealed. Calm years are easy; watch what happens
        when a crash starts.
      </p>
    </div>

    <div class="bench panel">
      <div class="eras" role="group" aria-label="Historical periods">
        <button v-for="(e, k) in ERAS" :key="e.name" type="button" :aria-pressed="k === era" @click="setEra(k)">
          {{ e.name }}
        </button>
      </div>

      <svg class="chart" :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="`SPY weekly closes with the range for the week ending ${longDate(target.d)}`">
        <g class="axis">
          <template v-for="t in yTicks" :key="t">
            <line :x1="M.l" :x2="W - M.r" :y1="Y(t)" :y2="Y(t)" />
            <text :x="M.l - 8" :y="Y(t) + 4" text-anchor="end">${{ Math.round(t) }}</text>
          </template>
          <text v-for="i in xTicks" :key="i" :x="X(i)" :y="H - 8" text-anchor="middle">{{ shortDate(rows[i].d) }}</text>
        </g>
        <line :x1="X(start)" :x2="X(start)" :y1="M.t" :y2="H - M.b" stroke="var(--accent)" stroke-dasharray="2 4" opacity="0.6" />
        <rect
          v-for="b in pastBands" :key="b.i" :x="X(b.i + 1) - 3.5" width="7" :y="Y(b.hi)" :height="Y(b.lo) - Y(b.hi)" rx="2"
          :fill="b.hit ? 'var(--band)' : 'var(--down)'" :opacity="b.hit ? 1 : 0.3"
        />
        <rect :x="X(cur + 1) - 10" width="20" :y="Y(call.hi!)" :height="Y(call.lo!) - Y(call.hi!)" rx="3" fill="var(--band)" stroke="var(--accent)" />
        <path :d="linePath" fill="none" stroke="var(--ink)" stroke-width="2" />
        <line :x1="X(cur)" :y1="Y(call.c)" :x2="X(cur + 1)" :y2="Y(target.c)" stroke="var(--ink)" stroke-width="2" stroke-dasharray="4 3" />
        <circle :cx="X(cur)" :cy="Y(call.c)" r="4" fill="var(--accent)" />
        <circle :cx="X(cur + 1)" :cy="Y(target.c)" r="4" fill="var(--panel)" stroke="var(--ink)" stroke-width="2" />
      </svg>

      <div class="ctrl">
        <button class="play" type="button" @click="playing ? stop() : play()">{{ playing ? '❚❚ Pause' : '▶ Play' }}</button>
        <input id="replay-week" v-model.number="pos" type="range" min="0" :max="SPAN - 1" aria-label="Week" @input="stop" />
        <span class="date">{{ shortDate(call.d) }} → {{ shortDate(target.d) }}</span>
      </div>

      <div class="verdict">
        <div>
          <div class="k">Range set {{ shortDate(call.d) }} · VIX {{ call.v.toFixed(1) }}</div>
          <div class="val">{{ money(call.lo!) }} – {{ money(call.hi!) }}</div>
          <div class="small">±{{ widthPct(call.s!).toFixed(1) }}% · lean {{ up ? '▲ up' : '▼ down' }} {{ pct(up ? call.p! : 1 - call.p!) }}</div>
        </div>
        <div>
          <div class="k">What happened {{ shortDate(target.d) }}</div>
          <div class="val">{{ money(target.c) }}</div>
          <div class="small">{{ change >= 0 ? '+' : '' }}{{ change.toFixed(1) }}% on the week</div>
        </div>
        <div>
          <div class="k">Grade</div>
          <div class="val">
            <span :class="rangeOk ? 'ok' : 'bad'">{{ rangeOk ? '✓' : '✗' }} range</span> ·
            <span :class="dirOk ? 'ok' : 'bad'">{{ dirOk ? '✓' : '✗' }} lean</span>
          </div>
        </div>
      </div>
      <div class="small">
        So far in this stretch: range {{ tally.range }}/{{ tally.n }}, direction lean {{ tally.dir }}/{{ tally.n }},
        "always up" {{ tally.up }}/{{ tally.n }}.
      </div>
    </div>
  </section>
</template>

<script lang="ts" setup>
import { computed, onUnmounted, ref } from 'vue'
import { longDate, money, pct, shortDate, ticks, widthPct, type Lab } from '../lib/lab'

const props = defineProps<{ lab: Lab }>()
const rows = computed(() => props.lab.rows)

const ERAS = [
  { name: '2008 financial crisis', from: '2008-08-01' },
  { name: '2011 debt-ceiling drop', from: '2011-06-03' },
  { name: '2018 Q4 selloff', from: '2018-08-31' },
  { name: '2020 COVID crash', from: '2020-01-10' },
  { name: '2022 bear market', from: '2021-12-03' },
  { name: 'Last 6 months', from: null },
]
const SPAN = 26 // weeks stepped through per era
const CONTEXT = 20 // weeks of history shown before the era starts

const era = ref(3)
const pos = ref(0)
const playing = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

// The last row's call isn't graded yet, so the latest era ends one week early.
const start = computed(() => {
  const from = ERAS[era.value].from
  return from ? rows.value.findIndex((r) => r.d >= from) : rows.value.length - 2 - SPAN + 1
})
const cur = computed(() => start.value + pos.value)
const call = computed(() => rows.value[cur.value])
const target = computed(() => rows.value[cur.value + 1])

function setEra(k: number) {
  stop()
  era.value = k
  pos.value = 0
}

function play() {
  if (pos.value >= SPAN - 1) pos.value = 0
  playing.value = true
  const slow = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  timer = setInterval(() => {
    if (pos.value >= SPAN - 1) return stop()
    pos.value++
  }, slow ? 900 : 550)
}

function stop() {
  clearInterval(timer)
  playing.value = false
}

onUnmounted(stop)

// chart geometry
// Narrow screens get a narrower drawing so axis labels stay readable when scaled to fit.
const narrowQuery = window.matchMedia('(max-width: 600px)')
const narrow = ref(narrowQuery.matches)
const onNarrow = (e: MediaQueryListEvent) => (narrow.value = e.matches)
narrowQuery.addEventListener('change', onNarrow)
onUnmounted(() => narrowQuery.removeEventListener('change', onNarrow))
const W = computed(() => (narrow.value ? 440 : 960))
const H = 320
const M = { l: 56, r: 16, t: 14, b: 28 }
const lo = computed(() => Math.max(0, start.value - CONTEXT))
const hi = computed(() => Math.min(rows.value.length - 1, start.value + SPAN))
const extent = computed(() => {
  const vals = rows.value.slice(lo.value, hi.value + 1).flatMap((r) => (r.lo != null ? [r.c, r.lo, r.hi!] : [r.c]))
  return [Math.min(...vals) * 0.985, Math.max(...vals) * 1.015]
})
const X = (i: number) => M.l + ((i - lo.value) / (hi.value - lo.value)) * (W.value - M.l - M.r)
const Y = (v: number) => {
  const [a, b] = extent.value
  return M.t + (1 - (v - a) / (b - a)) * (H - M.t - M.b)
}
const yTicks = computed(() => ticks(extent.value[0], extent.value[1], 5))
const xTicks = computed(() => {
  const out: number[] = []
  for (let i = lo.value; i <= hi.value; i += narrow.value ? 12 : 8) out.push(i)
  return out
})
const linePath = computed(() =>
  rows.value
    .slice(lo.value, cur.value + 1)
    .map((r, k) => `${k ? 'L' : 'M'}${X(lo.value + k)},${Y(r.c)}`)
    .join(''),
)
const pastBands = computed(() => {
  const out: { i: number; lo: number; hi: number; hit: boolean }[] = []
  for (let i = start.value; i < cur.value; i++) {
    const r = rows.value[i]
    if (r.lo == null || r.hi == null) continue
    const next = rows.value[i + 1].c
    out.push({ i, lo: r.lo, hi: r.hi, hit: next >= r.lo && next <= r.hi })
  }
  return out
})

// verdict for the current step
const up = computed(() => call.value.p! >= 0.5)
const change = computed(() => (target.value.c / call.value.c - 1) * 100)
const rangeOk = computed(() => target.value.c >= call.value.lo! && target.value.c <= call.value.hi!)
const dirOk = computed(() => target.value.c > call.value.c === up.value)
const tally = computed(() => {
  const g = props.lab.graded.filter((x) => x.i >= start.value && x.i <= cur.value)
  return {
    n: g.length,
    range: g.filter((x) => x.rangeHit).length,
    dir: g.filter((x) => x.dirHit).length,
    up: g.filter((x) => x.upWeek).length,
  }
})
</script>

<style scoped>
.bench {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.eras {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.eras button,
.play {
  font: 500 13px var(--f-body);
  border: 1px solid var(--rule);
  background: var(--bg);
  color: var(--ink);
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
}

.eras button[aria-pressed='true'] {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.ctrl {
  display: flex;
  gap: 12px;
  align-items: center;
}

.ctrl input {
  flex: 1;
  min-width: 0;
  accent-color: var(--accent);
}

.date {
  font-family: var(--f-data);
  font-size: 13px;
  min-width: 120px;
  text-align: right;
}

.verdict {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  font-size: 13.5px;
}

.verdict > div {
  border-top: 1px solid var(--rule);
  padding-top: 8px;
  min-width: 0;
}

.k {
  font-family: var(--f-data);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.val {
  font-family: var(--f-data);
  font-size: 15px;
}

@media (max-width: 760px) {
  .verdict {
    grid-template-columns: 1fr;
  }
}
</style>
