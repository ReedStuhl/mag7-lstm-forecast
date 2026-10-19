<template>
  <section id="record" class="section">
    <div>
      <div class="eyebrow">Scorecard</div>
      <h2>Every weekly call, graded on Friday</h2>
      <p class="lede">
        The range is the main promise: Friday's close should land inside it about 68% of the time.
        The direction lean is graded too, next to "always up", which is right whenever SPY rises,
        and it rises in most weeks.
      </p>
    </div>

    <div class="cards">
      <div v-for="c in cards" :key="c.label" class="stat">
        <div class="eyebrow">{{ c.label }}</div>
        <div class="v">{{ c.value }}</div>
        <div class="vs">{{ c.compare }}</div>
      </div>
    </div>

    <div class="ledger">
      <table>
        <tr>
          <th></th>
          <th v-for="(g, k) in last" :key="g.d" class="date">{{ k % 4 === 0 ? shortDate(g.d) : '' }}</th>
          <th class="date">now</th>
        </tr>
        <tr v-for="r in ledgerRows" :key="r.key" :class="{ primary: r.key === 'rangeHit' }">
          <th>{{ r.label }}</th>
          <td v-for="g in last" :key="g.d">
            <div class="cell" :class="[g[r.key] ? 'hit' : 'miss', { live: g.live }]" :title="longDate(g.d)">
              {{ g[r.key] ? '✓' : '✗' }}
            </div>
          </td>
          <td><div class="cell cur">?</div></td>
        </tr>
      </table>
      <div class="legend">
        <span><i class="sw" style="background: var(--up)"></i>Correct</span>
        <span><i class="sw" style="background: var(--down)"></i>Wrong</span>
        <span><i class="sw" style="border: 1.5px dashed var(--accent)"></i>This week, graded Friday</span>
        <span v-if="liveCount"><i class="sw live-sw"></i>Recorded live</span>
      </div>
      <p class="small provenance">
        Calls from {{ longDate(lab.file.launched) }} on are saved the weekend before and never changed.
        Earlier weeks come from the walk-forward backtest, where the model was retrained each January
        and never saw the weeks it was graded on.
        <template v-if="liveCount">Live so far: range {{ liveRange }}/{{ liveCount }}, direction {{ liveDir }}/{{ liveCount }}.</template>
      </p>
    </div>
  </section>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { longDate, pct, pct1, shortDate, type GradedWeek, type Lab } from '../lib/lab'

const props = defineProps<{ lab: Lab }>()
const all = computed(() => props.lab.graded)
const last = computed(() => all.value.slice(-26))
const count = (a: GradedWeek[], k: 'rangeHit' | 'dirHit' | 'upWeek') => a.filter((g) => g[k]).length

const cards = computed(() => [
  { label: 'Range · last 26 weeks', value: `${count(last.value, 'rangeHit')}/26`, compare: 'Target is about 68%, or 18 of 26' },
  {
    label: `Range · since ${all.value[0].d.slice(0, 4)}`,
    value: pct(count(all.value, 'rangeHit') / all.value.length),
    compare: `Over ${all.value.length} graded weeks, target 68%`,
  },
  {
    label: `Direction · since ${all.value[0].d.slice(0, 4)}`,
    value: pct1(count(all.value, 'dirHit') / all.value.length),
    compare: `"Always up": ${pct1(count(all.value, 'upWeek') / all.value.length)}`,
  },
])

const ledgerRows = [
  { key: 'rangeHit', label: 'Range' },
  { key: 'dirHit', label: 'Direction lean' },
  { key: 'upWeek', label: '"Always up"' },
] as const

const live = computed(() => all.value.filter((g) => g.live))
const liveCount = computed(() => live.value.length)
const liveRange = computed(() => count(live.value, 'rangeHit'))
const liveDir = computed(() => count(live.value, 'dirHit'))
</script>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.stat {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat .v {
  font-family: var(--f-data);
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}

.stat .vs {
  font-size: 13px;
  color: var(--muted);
}

.ledger {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  font-family: var(--f-data);
  font-size: 12px;
}

th {
  font-weight: 400;
  color: var(--muted);
  text-align: left;
  padding: 4px 10px 4px 0;
  white-space: nowrap;
}

th.date {
  padding: 0 3px;
  font-size: 10px;
}

tr.primary th {
  color: var(--ink);
  font-weight: 500;
}

td {
  padding: 3px;
}

.cell {
  width: 22px;
  height: 22px;
  border-radius: 4px;
  display: grid;
  place-items: center;
  font-size: 11px;
  color: #fff;
}

.cell.hit {
  background: var(--up);
}

.cell.miss {
  background: var(--down);
}

.cell.live {
  box-shadow: 0 0 0 2px var(--panel), 0 0 0 3.5px var(--accent);
}

.cell.cur {
  background: transparent;
  border: 1.5px dashed var(--accent);
  color: var(--accent);
}

.legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 12.5px;
  color: var(--muted);
  margin-top: 10px;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sw {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  display: inline-block;
}

.live-sw {
  background: var(--up);
  box-shadow: 0 0 0 1.5px var(--panel), 0 0 0 3px var(--accent);
}

.provenance {
  margin: 10px 0 0;
  max-width: 80ch;
}

@media (max-width: 760px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
