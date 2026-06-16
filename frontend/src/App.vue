<script setup lang="ts">
import { ref, onMounted, onUnmounted, provide } from 'vue'
import Sidebar from './components/app_layout/Sidebar.vue'
import Filelist from './components/macro_editor/Filelist.vue'
import Screencast from './components/screencast/Screencast.vue'
import ScreenCastCore from './components/screencast/ScreenCastCore.vue'
import Logeditor from './components/log_editor/Logeditor.vue'
import Settings from './components/settings/Settings.vue'
import './App.css'

type Theme = 'light' | 'dark'
type KeymouseSubView = {
  view: 'list' | 'editor'
  fileName: string
  content: string
}

const currentView = ref('hidden')
const isMaximized = ref(false)
const isScreencastFullscreen = ref(false)
const currentTheme = ref<Theme>('dark')
const hasNewLogError = ref(false)
const screencastMode = ref<'usb' | 'wireless' | null>(null)
const appInfo = ref({ name: 'AutoGame', version: '0.0.0', homepage: '', instructions: '' })
let logCheckInterval: number | null = null

// 对 ScreenCastView 的 ref
const screenCastViewRef = ref()

// 投屏全屏切换
function toggleScreencastFullscreen() {
  if (screencastMode.value && screenCastViewRef.value) {
    isScreencastFullscreen.value = !isScreencastFullscreen.value
    screenCastViewRef.value.toggleScrcpyFullscreen()
  }
}

// 保存 keymouse 视图的子状态
const keymouseSubView = ref<KeymouseSubView>({
  view: 'list',
  fileName: '',
  content: ''
})

const themeColors = {
  light: {
    bg: '#E0E9FF',
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
    const config = await window.pywebview.api.get_config_file()
    if (config.theme && (config.theme === 'light' || config.theme === 'dark')) {
      currentTheme.value = config.theme
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  }
}

async function loadAppInfo() {
  try {
    const info = await window.pywebview.api.get_app_info()
    appInfo.value = info
  } catch (e) {
    console.error('Failed to load app info:', e)
  }
}

async function saveTheme(theme: Theme) {
  try {
    const config = await window.pywebview.api.get_config_file()
    config.theme = theme
    await window.pywebview.api.save_config_file(config)
  } catch (e) {
    console.error('Failed to save config:', e)
  }
}

function toggleTheme() {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
  saveTheme(currentTheme.value)
}

async function checkNewLogError() {
  try {
    if (window.pywebview && window.pywebview.api) {
      hasNewLogError.value = await window.pywebview.api.has_new_error()
    }
  } catch (e) {
    console.error('Failed to check new log error:', e)
  }
}

async function clearNewLogErrorFlag() {
  try {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.clear_new_error_flag()
      hasNewLogError.value = false
    }
  } catch (e) {
    console.error('Failed to clear new log error flag:', e)
  }
}

function handleScreencastNavigate(mode: 'usb' | 'wireless') {
  screencastMode.value = mode
}

function handleScreencastBack() {
  screencastMode.value = null
  isScreencastFullscreen.value = false
}

function handleNavigate(id: string) {
  currentView.value = id
  screencastMode.value = null
  if (id === 'logs') {
    clearNewLogErrorFlag()
  }
}

function minimize() {
  try {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.minimize) {
      window.pywebview.api.minimize()
    }
  } catch (e) {
    console.error('Failed to minimize window:', e)
  }
}

function toggleMaximize() {
  try {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.toggle_maximize) {
      window.pywebview.api.toggle_maximize().then((result: boolean) => {
        isMaximized.value = result
      })
    }
  } catch (e) {
    console.error('Failed to toggle maximize:', e)
  }
}

function close() {
  try {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.close) {
      window.pywebview.api.close()
    }
  } catch (e) {
    console.error('Failed to close window:', e)
  }
}

async function pollForConfig() {
  const maxAttempts = 50
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      if (window.pywebview && window.pywebview.api) {
        await loadConfig()
        await loadAppInfo()
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

function handleGlobalKeydown(e: KeyboardEvent) {
  if (e.key === 'Tab') {
    e.preventDefault()
  }
}

onMounted(() => {
  // 全局禁用 Tab 切换焦点的默认行为
  window.addEventListener('keydown', handleGlobalKeydown, true)

  pollForConfig()
  // 每秒检查一次是否有新的错误
  if (typeof window.setInterval === 'function') {
    logCheckInterval = window.setInterval(checkNewLogError, 1000)
  }

  // 暴露投屏全屏切换函数给 Python 调用
  // 同时暴露安全的默认实现给 jsoneditor 相关函数
  if (typeof window !== 'undefined') {
    window.toggleScreencastFullscreen = toggleScreencastFullscreen

    // 安全的默认实现，不执行任何操作
    window.disableJsonEditor = () => {
      // 仅在 jsoneditor 组件中有效
    }
    window.enableJsonEditor = () => {
      // 仅在 jsoneditor 组件中有效
    }
    window.saveFile = () => {
      // 仅在 jsoneditor 组件中有效
    }
  }
})

onUnmounted(() => {
  if (logCheckInterval !== null) {
    clearInterval(logCheckInterval)
  }
  window.removeEventListener('keydown', handleGlobalKeydown, true)
})

provide('theme', currentTheme)
provide('themeColors', themeColors)
provide('toggleTheme', toggleTheme)
provide('appInfo', appInfo)
</script>

<style src="./App.css" scoped></style>

<template>
  <div class="app-container" :data-theme="currentTheme">
    <div v-if="!isScreencastFullscreen" class="title-bar pywebview-drag-region">
      <span class="app-name">{{ appInfo.name }}</span>
      <div class="title"></div>
      <div class="window-controls">
        <button class="control-btn minimize-btn" @click="minimize">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="4" y="12" width="16" height="1" rx="1" />
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
      <Sidebar v-if="!isScreencastFullscreen" class="sidebar" :has-new-log-error="hasNewLogError" @navigate="handleNavigate" />
      <main class="content">
        <div class="view-container">
          <div v-if="currentView === 'hidden'" class="hidden-view"></div>
          <Filelist
            v-else-if="currentView === 'keymouse'"
            :initialSubView="keymouseSubView.view"
            :initialFileName="keymouseSubView.fileName"
            :initialContent="keymouseSubView.content"
            @updateSubView="keymouseSubView.view = $event"
            @updateFileName="keymouseSubView.fileName = $event"
            @updateContent="keymouseSubView.content = $event"
          />
          <ScreenCastCore
            ref="screenCastViewRef"
            v-else-if="screencastMode"
            :connectionMode="screencastMode"
            @back="handleScreencastBack"
            @fullscreen-change="isScreencastFullscreen = $event"
          />
          <Screencast
            v-else-if="currentView === 'screencast'"
            @navigate="handleScreencastNavigate"
          />
          <Settings v-else-if="currentView === 'settings'" />
          <Logeditor
            v-else-if="currentView === 'logs'"
          />
        </div>
      </main>
    </div>
  </div>
</template>
