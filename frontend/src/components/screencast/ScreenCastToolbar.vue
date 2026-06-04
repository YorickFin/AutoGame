<template>
  <div class="viewer-sidebar viewer-sidebar-right">
    <div class="sidebar-top">
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="$emit('toggle-key-mapping')"
          @mouseenter="$emit('show-tooltip', 'scrcpy-expand-screen', '键位映射')"
          @mouseleave="$emit('hide-tooltip', 'scrcpy-expand-screen')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="4" width="20" height="16" rx="2" ry="2"/>
            <line x1="7" y1="10" x2="10" y2="10"/>
            <line x1="14" y1="10" x2="17" y2="10"/>
            <line x1="4" y1="15" x2="7" y2="15"/>
            <line x1="10" y1="15" x2="14" y2="15"/>
            <line x1="17" y1="15" x2="20" y2="15"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['scrcpy-expand-screen']" class="tooltip tooltip-left">
            {{ hoveredButtons['scrcpy-expand-screen'] }}
          </div>
        </Transition>
      </div>
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="$emit('scrcpy-vol-up')"
          @mouseenter="$emit('show-tooltip', 'scrcpy-vol-up', '音量+')"
          @mouseleave="$emit('hide-tooltip', 'scrcpy-vol-up')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <line x1="14" y1="12" x2="24" y2="12"/>
            <line x1="19" y1="7" x2="19" y2="17"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['scrcpy-vol-up']" class="tooltip tooltip-left">
            {{ hoveredButtons['scrcpy-vol-up'] }}
          </div>
        </Transition>
      </div>
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="$emit('scrcpy-vol-down')"
          @mouseenter="$emit('show-tooltip', 'scrcpy-vol-down', '音量-')"
          @mouseleave="$emit('hide-tooltip', 'scrcpy-vol-down')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <line x1="14" y1="12" x2="24" y2="12"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['scrcpy-vol-down']" class="tooltip tooltip-left">
            {{ hoveredButtons['scrcpy-vol-down'] }}
          </div>
        </Transition>
      </div>
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="$emit('toggle-fullscreen')"
          @mouseenter="$emit('show-tooltip', 'scrcpy-fullscreen', isFullscreen ? '退出全屏' : '全屏')"
          @mouseleave="$emit('hide-tooltip', 'scrcpy-fullscreen')"
        >
          <svg v-if="!isFullscreen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 3 21 3 21 9"/>
            <polyline points="9 21 3 21 3 15"/>
            <line x1="21" y1="3" x2="14" y2="10"/>
            <line x1="3" y1="21" x2="10" y2="14"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 9 3 9 3 3"/>
            <polyline points="15 15 21 15 21 21"/>
            <line x1="3" y1="9" x2="10" y2="2"/>
            <line x1="21" y1="15" x2="14" y2="22"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['scrcpy-fullscreen']" class="tooltip tooltip-left">
            {{ hoveredButtons['scrcpy-fullscreen'] }}
          </div>
        </Transition>
      </div>
      <div class="btn-wrapper">
        <button
          class="action-btn"
          :class="{ active: showFps }"
          @click="$emit('toggle-fps')"
          @mouseenter="$emit('show-tooltip', 'toggle-fps', showFps ? '隐藏帧率' : '显示帧率')"
          @mouseleave="$emit('hide-tooltip', 'toggle-fps')"
        >
          <svg viewBox="0 0 24 24" width="20" height="20">
            <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" fill="none"/>
            <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="2" fill="none"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['toggle-fps']" class="tooltip tooltip-left">
            {{ hoveredButtons['toggle-fps'] }}
          </div>
        </Transition>
      </div>
    </div>
    <div class="sidebar-bottom">
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="$emit('scrcpy-back')"
          @mouseenter="$emit('show-tooltip', 'scrcpy-back', '返回')"
          @mouseleave="$emit('hide-tooltip', 'scrcpy-back')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['scrcpy-back']" class="tooltip tooltip-left">
            {{ hoveredButtons['scrcpy-back'] }}
          </div>
        </Transition>
      </div>
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="$emit('scrcpy-switch-app')"
          @mouseenter="$emit('show-tooltip', 'scrcpy-switch-app', '多应用')"
          @mouseleave="$emit('hide-tooltip', 'scrcpy-switch-app')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['scrcpy-switch-app']" class="tooltip tooltip-left">
            {{ hoveredButtons['scrcpy-switch-app'] }}
          </div>
        </Transition>
      </div>
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="$emit('scrcpy-home')"
          @mouseenter="$emit('show-tooltip', 'scrcpy-home', '主页')"
          @mouseleave="$emit('hide-tooltip', 'scrcpy-home')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['scrcpy-home']" class="tooltip tooltip-left">
            {{ hoveredButtons['scrcpy-home'] }}
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import "./ScreenCastToolbar.css"
defineProps<{
  isFullscreen: boolean
  showFps: boolean
  hoveredButtons: Record<string, string>
}>()

defineEmits<{
  (e: 'toggle-key-mapping'): void
  (e: 'scrcpy-vol-up'): void
  (e: 'scrcpy-vol-down'): void
  (e: 'toggle-fullscreen'): void
  (e: 'toggle-fps'): void
  (e: 'scrcpy-back'): void
  (e: 'scrcpy-switch-app'): void
  (e: 'scrcpy-home'): void
  (e: 'show-tooltip', key: string, text: string): void
  (e: 'hide-tooltip', key: string): void
}>()
</script>
