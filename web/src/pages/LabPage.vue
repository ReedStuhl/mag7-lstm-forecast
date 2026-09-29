<template>
  <div>
    <header class="max-w-3xl mx-auto px-6 pt-10 pb-6 text-center">
      <router-link to="/" class="text-sm text-gray-500 hover:text-gray-700 transition"
        >&larr; Back to forecasts</router-link
      >
      <h1 class="text-3xl sm:text-4xl font-bold mt-3">Prediction Lab</h1>
      <p class="mt-3 text-gray-600">
        A place to mess with these models directly instead of just reading about them - see how
        the algorithm, the window of data, and (fictionally) the news mood all change what comes
        out the other end. NVDA only, for now.
      </p>
    </header>

    <main class="max-w-3xl mx-auto px-6 pb-16 space-y-8">
      <section v-if="loading" class="text-center text-sm text-gray-400 py-12">Loading lab data...</section>

      <template v-else-if="loadError">
        <p class="text-center text-sm text-red-500 py-12">Couldn't load lab data. Try refreshing.</p>
      </template>

      <template v-else-if="labModels && labWindows">
        <LabModelComparison :data="labModels" />
        <PredictionPlayground :data="labWindows" />
        <LabEssay />
      </template>
    </main>

    <footer class="max-w-3xl mx-auto px-6 pb-10 text-center text-xs text-gray-400 space-y-1">
      <p>Educational demo only - not financial or investment advice.</p>
    </footer>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import LabModelComparison from '../components/LabModelComparison.vue'
import PredictionPlayground from '../components/PredictionPlayground.vue'
import LabEssay from '../components/LabEssay.vue'
import type { LabModelsFile, LabWindowsFile } from '../types'

const loading = ref(true)
const loadError = ref(false)
const labModels = ref<LabModelsFile | null>(null)
const labWindows = ref<LabWindowsFile | null>(null)

onMounted(async () => {
  try {
    const [m, w] = await Promise.all([
      fetch('/data/lab_models.json').then((r) => r.json()),
      fetch('/data/lab_windows.json').then((r) => r.json()),
    ])
    labModels.value = m
    labWindows.value = w
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})
</script>
