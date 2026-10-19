<template>
  <section id="experiment" class="section">
    <div>
      <div class="eyebrow">The experiment</div>
      <h2>Can a model call next week's direction? We tried four.</h2>
      <p class="lede">
        Each model was retrained every January on everything before it, then tested on each week of
        that year. The test covers {{ base.weeks.toLocaleString() }} weeks from
        {{ exp.test_start.slice(0, 4) }} to now. The bar to clear is "always up", which needs no model at all.
      </p>
    </div>

    <div class="exp panel">
      <div class="tbl">
        <table>
          <tr>
            <th>Model</th>
            <th>Accuracy</th>
            <th class="dotcell">vs. "always up" <span class="nocase">({{ pct(scale[0]) }}–{{ pct(scale[1]) }})</span></th>
            <th>Calls "down"</th>
            <th>Right when "down"</th>
          </tr>
          <tr v-for="m in models" :key="m.key" :class="{ base: m.key === 'always_up' }">
            <td>{{ m.name }}<span class="sub">{{ m.inputs }}</span></td>
            <td class="num">{{ pct1(m.metrics.accuracy) }}</td>
            <td class="dotcell">
              <svg :viewBox="`0 0 ${DW} 26`" :style="{ maxWidth: DW + 'px' }" aria-hidden="true">
                <line x1="8" :x2="DW - 8" y1="13" y2="13" stroke="var(--rule)" />
                <line :x1="dotX(base.accuracy)" :x2="dotX(base.accuracy)" y1="3" y2="23" stroke="var(--naive)" stroke-dasharray="3 2" />
                <circle :cx="dotX(m.metrics.accuracy)" cy="13" r="5.5" :fill="m.metrics.accuracy >= base.accuracy ? 'var(--naive)' : 'var(--down)'" />
              </svg>
            </td>
            <td class="num">{{ m.metrics.down_call_share ? pct(m.metrics.down_call_share) + ' of weeks' : 'never' }}</td>
            <td class="num">{{ m.metrics.down_call_accuracy != null ? pct(m.metrics.down_call_accuracy) : '—' }}</td>
          </tr>
        </table>
      </div>
      <div class="takeaway">
        <div v-if="!winners.length">
          <strong>None of them beat "always up".</strong>
          The gaps are small enough to be noise, and they all point the wrong way. Adding VIX and
          interest rates made the models change their minds more often, not more accurately.
        </div>
        <div v-else>
          <strong>{{ winners.map((m) => m.name).join(', ') }} edged past "always up" in this week's rerun.</strong>
          <template v-if="winners.some((m) => m.metrics.mcnemar_p_vs_always_up < 0.05)">The difference passes a significance test, which is worth a closer look.</template>
          <template v-else>The gap is small enough to be noise (it fails a significance test), so the lean still isn't the headline.</template>
        </div>
        <div v-if="downCallers.every((m) => m.metrics.down_call_accuracy! < 0.5)">
          <strong>Their "down" calls were worse than a coin flip.</strong>
          Every model was right less than half the time when it called a down week. More
          confidence in "down" just meant more misses.
        </div>
        <div v-else>
          <strong>"Down" calls are the hard part.</strong>
          The table shows how often each model called a down week and how often it was right when it did.
        </div>
      </div>
    </div>

    <div class="exp panel">
      <div class="eyebrow">Range methods · same test weeks</div>
      <div class="tbl">
        <table>
          <tr>
            <th>Method</th>
            <th>Caught next close</th>
            <th>Average width</th>
            <th>Worst year</th>
            <th>Best year</th>
          </tr>
          <tr v-for="r in ranges" :key="r.key">
            <td>{{ r.name }}</td>
            <td class="num">{{ pct(r.metrics.coverage) }}</td>
            <td class="num">±{{ r.metrics.avg_half_width_pct.toFixed(1) }}%</td>
            <td class="num">{{ pct(r.metrics.worst_year_coverage) }}</td>
            <td class="num">{{ pct(r.metrics.best_year_coverage) }}</td>
          </tr>
        </table>
      </div>
      <p class="small note">
        This site uses the scaled VIX range. VIX usually overstates how much the market actually
        moves, so it's shrunk each January to the size that would have caught 68% of earlier weeks.
        No range catches the biggest weekly moves; a crash outruns everything.
      </p>
    </div>
  </section>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import { pct, pct1, type Lab } from '../lib/lab'

const props = defineProps<{ lab: Lab }>()
const exp = computed(() => props.lab.file.experiment)
const base = computed(() => exp.value.direction.always_up)

const MODEL_NAMES: Record<string, [string, string]> = {
  always_up: ['Always up', 'Baseline: no model'],
  logistic_price: ['Logistic regression', 'Recent returns, volatility, moving averages'],
  logistic_context: ['Logistic regression', 'Same, plus VIX and interest rates'],
  boosted_trees: ['Boosted trees', 'Same inputs as above · used for the lean'],
  lstm_context: ['LSTM', 'Last 26 weeks of the same inputs'],
}
const RANGE_NAMES: Record<string, string> = {
  trailing_52w: "Last 52 weeks' volatility",
  ewma: 'Recent-weighted volatility',
  vix_implied: 'VIX, as quoted',
  vix_scaled: 'VIX, scaled each January (used here)',
}

const models = computed(() =>
  Object.entries(exp.value.direction).map(([key, metrics]) => ({
    key,
    name: MODEL_NAMES[key]?.[0] ?? key,
    inputs: MODEL_NAMES[key]?.[1] ?? '',
    metrics,
  })),
)
const winners = computed(() =>
  models.value.filter((m) => m.key !== 'always_up' && m.metrics.accuracy > base.value.accuracy),
)
const downCallers = computed(() => models.value.filter((m) => m.metrics.down_call_accuracy != null))
const ranges = computed(() =>
  Object.entries(exp.value.range).map(([key, metrics]) => ({ key, name: RANGE_NAMES[key] ?? key, metrics })),
)

// dot plot zoomed to the accuracies, padded to whole percents
const DW = 240
const scale = computed(() => {
  const accs = models.value.map((m) => m.metrics.accuracy)
  return [Math.floor(Math.min(...accs) * 100 - 1) / 100, Math.ceil(Math.max(...accs) * 100 + 1) / 100]
})
const dotX = (v: number) => 8 + ((v - scale.value[0]) / (scale.value[1] - scale.value[0])) * (DW - 16)
</script>

<style scoped>
.exp {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tbl {
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  width: 100%;
  min-width: 640px;
  font-size: 13.5px;
}

th {
  font-family: var(--f-data);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 400;
  text-align: left;
  padding: 6px 10px 6px 0;
  border-bottom: 1px solid var(--rule);
}

.nocase {
  text-transform: none;
}

td {
  padding: 9px 10px 9px 0;
  border-bottom: 1px solid var(--rule);
  font-variant-numeric: tabular-nums;
  vertical-align: middle;
}

td.num {
  font-family: var(--f-data);
  font-size: 13px;
  white-space: nowrap;
}

tr.base td {
  color: var(--muted);
}

.sub {
  display: block;
  font-size: 12px;
  color: var(--muted);
}

.dotcell {
  width: 34%;
}

.dotcell svg {
  width: 100%;
  display: block;
}

.takeaway {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.takeaway div {
  border-left: 3px solid var(--accent);
  padding: 2px 0 2px 14px;
  font-size: 14px;
  color: var(--muted);
  min-width: 0;
}

.takeaway strong {
  color: var(--ink);
  display: block;
  margin-bottom: 2px;
}

.note {
  margin: 0;
}

@media (max-width: 760px) {
  .takeaway {
    grid-template-columns: 1fr;
  }
}
</style>
