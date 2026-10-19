<template>
  <div class="wrap">
    <header class="top">
      <div class="brand">SPY <span>Prediction</span> Lab</div>
      <nav>
        <a href="#call">This week</a>
        <a href="#record">Record</a>
        <a href="#replay">Replay</a>
        <a href="#experiment">The experiment</a>
      </nav>
    </header>

    <p v-if="loading" class="status small">Loading this week's numbers...</p>
    <p v-else-if="!lab" class="status bad">Couldn't load the data. Try refreshing the page.</p>

    <template v-else>
      <ThisWeek :lab="lab" />
      <Scorecard :lab="lab" />
      <Replay :lab="lab" />
      <Experiment :lab="lab" />
    </template>

    <footer class="small">
      <p>
        Updated every weekend from Yahoo Finance data<template v-if="lab">, last on {{ longDate(lab.file.updated) }}</template>.
        Code and the full experiment are on <a href="https://github.com/ReedStuhl/mag7-lstm-forecast">GitHub</a>.
      </p>
      <p>Educational project, not financial or investment advice.</p>
    </footer>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref, shallowRef } from 'vue'
import ThisWeek from './components/ThisWeek.vue'
import Scorecard from './components/Scorecard.vue'
import Replay from './components/Replay.vue'
import Experiment from './components/Experiment.vue'
import { loadLab, longDate, type Lab } from './lib/lab'

const lab = shallowRef<Lab | null>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    lab.value = await loadLab()
  } catch {
    lab.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wrap {
  max-width: 1040px;
  margin: 0 auto;
  padding-inline: 20px;
  padding-block: 24px 48px;
  display: flex;
  flex-direction: column;
  gap: 36px;
}

.top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.brand {
  font-family: var(--f-display);
  font-stretch: 118%;
  font-weight: 800;
  font-size: 15px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.brand span {
  color: var(--accent);
}

nav {
  display: flex;
  gap: 18px;
  font-size: 14px;
  flex-wrap: wrap;
}

nav a {
  color: var(--muted);
  text-decoration: none;
}

nav a:hover {
  color: var(--ink);
}

.status {
  padding-block: 48px;
  text-align: center;
}

footer {
  border-top: 1px solid var(--rule);
  padding-top: 16px;
}

footer p {
  margin: 0 0 4px;
}
</style>
