<template>
  <button
    type="button"
    class="px-3 py-1.5 text-xs border rounded-lg border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
    @click="toggle"
  >
    {{ isDark ? 'Light mode' : 'Dark mode' }}
  </button>
</template>

<script lang="ts" setup>
import { onMounted, ref } from 'vue'

const isDark = ref(false)

function toggle() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
  try {
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  } catch {
    // ignore (private browsing, blocked storage, etc.)
  }
}

onMounted(() => {
  try {
    const saved = localStorage.getItem('theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDark.value = saved ? saved === 'dark' : prefersDark
  } catch {
    isDark.value = false
  }
  document.documentElement.classList.toggle('dark', isDark.value)
})
</script>
