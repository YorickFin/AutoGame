<script setup lang="ts">
import { ref, inject, type Ref } from 'vue'

type Theme = 'light' | 'dark'

const currentTheme = inject<Ref<Theme>>('theme')
const toggleTheme = inject<() => void>('toggleTheme')
const appInfo = inject<Ref<{ name: string; version: string; homepage: string; instructions: string }>>('appInfo')

const minimizeToTray = ref(true)
const macroSwitch = ref('F1')
const isListening = ref(false)
const macroSwitchInput = ref<HTMLInputElement | null>(null)
let listenInterval: ReturnType<typeof setInterval> | null = null

async function loadConfig() {
  try {
    const config = await (window as any).pywebview.api.get_config_file()
    if (config.minimizeToTray !== undefined) {
      minimizeToTray.value = config.minimizeToTray
    }
    if (config.macroSwitch !== undefined) {
      macroSwitch.value = config.macroSwitch
    }
  } catch (e) {
    console.error('Failed to load config:', e)
  }
}

async function saveMinimizeToTray(value: boolean) {
  try {
    const config = await (window as any).pywebview.api.get_config_file()
    config.minimizeToTray = value
    await (window as any).pywebview.api.save_config_file(config)
  } catch (e) {
    console.error('Failed to save config:', e)
  }
}

async function saveMacroSwitch(value: string) {
  try {
    const config = await (window as any).pywebview.api.get_config_file()
    config.macroSwitch = value
    await (window as any).pywebview.api.save_config_file(config)
  } catch (e) {
    console.error('Failed to save macroSwitch:', e)
  }
}

async function startListening() {
  if (listenInterval) return
  isListening.value = true
  listenInterval = setInterval(async () => {
    try {
      const keyName = await (window as any).pywebview.api.get_macro_switch_key_name()
      if (keyName) {
        if (keyName !== macroSwitch.value) {
          macroSwitch.value = keyName;
          saveMacroSwitch(keyName);
        }
        stopListening();
      }
    } catch (e) {
      // ignore errors during listening
    }
  }, 100)
}

function stopListening() {
  if (listenInterval) {
    clearInterval(listenInterval)
    listenInterval = null
  }
  isListening.value = false
  if (macroSwitchInput.value) {
    macroSwitchInput.value.blur()
  }
}

function onMacroSwitchFocus() {
  startListening()
}

function onMacroSwitchBlur() {
}

async function openUrl(url: string) {
  try {
    if ((window as any).pywebview && (window as any).pywebview.api) {
      await (window as any).pywebview.api.open_url(url)
    }
  } catch (e) {
    console.error('Failed to open url:', e)
  }
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

import { onMounted } from 'vue'
onMounted(() => {
  pollForConfig()
})
</script>

<style src="./Settings.css" scoped></style>

<template>
  <div class="settings-view" :data-theme="currentTheme">
    <h1 class="section-title">设置</h1>
    <div class="scroll-container">
      <div class="settings-content">
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
        <div class="setting-item">
          <span class="setting-label">关闭主界面</span>
          <div class="radio-group">
            <label class="radio-option" :class="{ active: minimizeToTray }">
              <input type="radio" name="closeAction" :checked="minimizeToTray" @change="minimizeToTray = true; saveMinimizeToTray(true)" />
              <span>最小化到托盘</span>
            </label>
            <label class="radio-option" :class="{ active: !minimizeToTray }">
              <input type="radio" name="closeAction" :checked="!minimizeToTray" @change="minimizeToTray = false; saveMinimizeToTray(false)" />
              <span>退出程序</span>
            </label>
          </div>
        </div>
        <div class="setting-item">
          <span class="setting-label">宏开关</span>
          <input
            ref="macroSwitchInput"
            type="text"
            class="macro-switch-input"
            :value="macroSwitch"
            @focus="onMacroSwitchFocus"
            @blur="onMacroSwitchBlur"
            readonly
          />
        </div>
      </div>
    </div>
    <div class="action-buttons">
      <button class="action-btn" @click="openUrl(appInfo?.homepage || '')">GitHub</button>
      <button class="action-btn" @click="openUrl(appInfo?.instructions || '')">使用说明</button>
    </div>
    <div class="app-info">
      <span>{{ appInfo?.name }}  version: {{ appInfo?.version }}</span>
    </div>
  </div>
</template>
