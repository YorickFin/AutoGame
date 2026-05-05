<script setup lang="ts">
import { ref, onMounted, provide } from 'vue'
import Sidebar from './components/Sidebar.vue'

type Theme = 'light' | 'dark'

const currentView = ref('hidden')
const isMaximized = ref(false)
const currentTheme = ref<Theme>('dark')

const themeColors = {
  light: {
    bg: '#EDE8EE',
    bgSecondary: '#E5DFE6',
    bgTertiary: '#D9D2DA',
    text: '#1F2430',
    textSecondary: '#4A5060',
    hover: 'rgba(0, 0, 0, 0.08)'
  },
  dark: {
    bg: '#1F2430',
    bgSecondary: '#1a1a2e',
    bgTertiary: '#0f0f1a',
    text: '#e0e0e0',
    textSecondary: '#9ca3af',
    hover: 'rgba(255, 255, 255, 0.08)'
  }
}

async function loadConfig() {
  try {
    const config = await (window as any).pywebview.api.get_config()
    if (config.theme && (config.theme === 'light' || config.theme === 'dark')) {
      currentTheme.value = config.theme
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  }
}

async function saveTheme(theme: Theme) {
  try {
    const config = await (window as any).pywebview.api.get_config()
    config.theme = theme
    await (window as any).pywebview.api.save_config(config)
  } catch (e) {
    console.error('Failed to save config:', e)
  }
}

function toggleTheme() {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
  saveTheme(currentTheme.value)
}

function handleNavigate(id: string) {
  currentView.value = id
}

async function minimize() {
  await (window as any).pywebview.api.minimize()
}

async function toggleMaximize() {
  isMaximized.value = await (window as any).pywebview.api.toggle_maximize()
}

async function close() {
  await (window as any).pywebview.api.close()
}

async function pollForConfig() {
  const maxAttempts = 50
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      if ((window as any).pywebview && (window as any).pywebview.api) {
        await loadConfig()
        return
      }
    } catch (e) {
      // 继续尝试
    }
    attempts++
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  console.warn('Failed to load config after multiple attempts')
}

onMounted(() => {
  pollForConfig()
})

provide('theme', currentTheme)
provide('themeColors', themeColors)
provide('toggleTheme', toggleTheme)
</script>

<template>
  <div class="app-container" :data-theme="currentTheme">
    <div class="title-bar">
      <div class="title"></div>
      <div class="window-controls">
        <button class="control-btn minimize-btn" @click="minimize">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="4" y="14" width="16" height="2" rx="1" />
          </svg>
        </button>
        <button class="control-btn maximize-btn" @click="toggleMaximize">
          <svg v-if="!isMaximized" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M4 4h16v16H4z" stroke-linejoin="round" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M10 5h9v9h-9zM5 10h9v9H5z" stroke-linejoin="round" />
          </svg>
        </button>
        <button class="control-btn close-btn" @click="close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M5 5l14 14M19 5l-14 14" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>
    </div>
    <div class="main-container">
      <Sidebar class="sidebar" @navigate="handleNavigate" />
      <main class="content">
        <div class="view-container">
          <div v-if="currentView === 'hidden'" class="hidden-view"></div>
          <h1 v-else-if="currentView !== 'settings'">{{ currentView === 'keymouse' ? '键鼠控制' : '手机投屏' }}</h1>
          <div v-if="currentView === 'settings'" class="settings-content">
            <div class="setting-item">
              <span class="setting-label">主题模式</span>
              <button class="theme-toggle-btn" @click="toggleTheme">
                <svg v-if="currentTheme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="5"/>
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
                <span>{{ currentTheme === 'dark' ? '明亮模式' : '暗黑模式' }}</span>
              </button>
            </div>
          </div>
          <p v-else-if="currentView !== 'hidden'">内容区域 - {{ currentView }}</p>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.app-container[data-theme="dark"] {
  background-color: #1F2430;
}

.app-container[data-theme="light"] {
  background-color: #EDE8EE;
}

.title-bar {
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  cursor: default;
  user-select: none;
  -webkit-app-region: drag;
}

.app-container[data-theme="dark"] .title-bar {
  background-color: #1F2430;
}

.app-container[data-theme="light"] .title-bar {
  background-color: #EDE8EE;
}

.title {
  color: #e0e0e0;
  font-size: 14px;
  font-weight: 500;
}

.app-container[data-theme="light"] .title {
  color: #1F2430;
}

.window-controls {
  display: flex;
  gap: 4px;
  -webkit-app-region: no-drag;
}

.control-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.app-container[data-theme="dark"] .control-btn {
  color: #9ca3af;
}

.app-container[data-theme="light"] .control-btn {
  color: #4A5060;
}

.app-container[data-theme="dark"] .control-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #f3f4f6;
}

.app-container[data-theme="light"] .control-btn:hover {
  background-color: rgba(0, 0, 0, 0.1);
  color: #1F2430;
}

.close-btn:hover {
  background-color: #ef4444 !important;
  color: #fff !important;
}

.control-btn svg {
  width: 14px;
  height: 14px;
  transition: transform 0.15s ease;
}

.control-btn:hover svg {
  transform: scale(1.05);
}

.main-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar {
  flex: 0 0 60px;
}

.content {
  flex: 1;
  display: flex;
}

.app-container[data-theme="dark"] .content {
  background-color: #1F2430;
}

.app-container[data-theme="light"] .content {
  background-color: #EDE8EE;
}

.view-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.app-container[data-theme="dark"] .view-container {
  color: #e0e0e0;
}

.app-container[data-theme="light"] .view-container {
  color: #1F2430;
}

.view-container h1 {
  font-size: 24px;
  margin-bottom: 16px;
}

.view-container p {
  font-size: 16px;
  color: #888;
}

.app-container[data-theme="light"] .view-container p {
  color: #4A5060;
}

.settings-content {
  width: 100%;
  max-width: 500px;
  padding: 24px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 12px;
}

.app-container[data-theme="dark"] .setting-item {
  background-color: rgba(255, 255, 255, 0.05);
}

.app-container[data-theme="light"] .setting-item {
  background-color: rgba(0, 0, 0, 0.05);
}

.setting-label {
  font-size: 16px;
  font-weight: 500;
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.app-container[data-theme="dark"] .theme-toggle-btn {
  background-color: #4A5060;
  color: #e0e0e0;
}

.app-container[data-theme="light"] .theme-toggle-btn {
  background-color: #4A5060;
  color: #ffffff;
}

.theme-toggle-btn:hover {
  transform: translateY(-1px);
}

.theme-toggle-btn svg {
  width: 18px;
  height: 18px;
}

.hidden-view {
  width: 100%;
  height: 100%;
}
</style>
