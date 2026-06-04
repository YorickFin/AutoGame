<script setup lang="ts">
import { ref, inject, type Ref } from 'vue'

type Theme = 'light' | 'dark'

interface MenuItem {
  id: string
  label: string
  icon: string
}

const menuItems: MenuItem[] = [
  { id: 'keymouse', label: '键鼠控制', icon: '' },
  { id: 'screencast', label: '手机投屏', icon: '' },
]

const props = defineProps<{
  hasNewLogError?: boolean
}>()

const hoveredItem = ref<string | null>(null)
const currentTheme = inject<Ref<Theme>>('theme')

const emit = defineEmits<{
  (e: 'navigate', id: string): void
}>()

function handleClick(id: string) {
  emit('navigate', id)
}
</script>

<template>
  <div class="sidebar" :data-theme="currentTheme">
    <div class="menu-top">
      <div
        v-for="item in menuItems"
        :key="item.id"
        class="menu-item"
        @mouseenter="hoveredItem = item.id"
        @mouseleave="hoveredItem = null"
        @click="handleClick(item.id)"
      >
        <div class="icon-placeholder">
          <svg v-if="item.id === 'keymouse'" viewBox="0 0 24 24" fill="none">
            <rect x="2" y="5" width="18" height="11" rx="1.5" :fill="currentTheme === 'dark' ? '#4a9eff' : '#60a5fa'" :stroke="currentTheme === 'dark' ? '#ffffff' : '#374151'" stroke-width="1"/>
            <rect x="4" y="7" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="7" y="7" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="10" y="7" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="13" y="7" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="4" y="10" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="7" y="10" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="10" y="10" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="13" y="10" width="2.5" height="2" rx="0.5" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <ellipse cx="18" cy="17" rx="4" ry="5" :fill="currentTheme === 'dark' ? '#8b5cf6' : '#a78bfa'" :stroke="currentTheme === 'dark' ? '#ffffff' : '#374151'" stroke-width="1"/>
            <ellipse cx="18" cy="15" rx="1.5" ry="1" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <ellipse cx="18" cy="18.5" rx="1.5" ry="1" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <line x1="18" y1="15.8" x2="18" y2="17.5" :stroke="currentTheme === 'dark' ? '#ffffff' : '#374151'" stroke-width="1"/>
          </svg>
          <svg v-else-if="item.id === 'screencast'" viewBox="0 0 24 24" fill="none">
            <rect x="1" y="4" width="19" height="13" rx="2" :fill="currentTheme === 'dark' ? '#6366f1' : '#818cf8'" :stroke="currentTheme === 'dark' ? '#ffffff' : '#374151'" stroke-width="1"/>
            <rect x="3" y="6" width="15" height="9" rx="0.5" :fill="currentTheme === 'dark' ? '#1a1a2e' : '#374151'"/>
            <rect x="10" y="15.5" width="1" height="2" rx="0.3" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
            <rect x="12" y="8" width="9" height="13" rx="1.5" :fill="currentTheme === 'dark' ? '#10b981' : '#34d399'" :stroke="currentTheme === 'dark' ? '#ffffff' : '#374151'" stroke-width="1"/>
            <rect x="13.5" y="9.5" width="6" height="9" rx="0.5" :fill="currentTheme === 'dark' ? '#1a1a2e' : '#374151'"/>
            <circle cx="16.5" cy="20.5" r="0.8" :fill="currentTheme === 'dark' ? '#ffffff' : '#374151'"/>
          </svg>
        </div>
        <Transition name="tooltip">
          <div v-if="hoveredItem === item.id" class="tooltip">
            {{ item.label }}
          </div>
        </Transition>
      </div>
    </div>
    <div class="menu-bottom">
      <div
        class="menu-item"
        @mouseenter="hoveredItem = 'logs'"
        @mouseleave="hoveredItem = null"
        @click="handleClick('logs')"
      >
        <div class="icon-placeholder">
          <svg viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="2" fill="none" :stroke="currentTheme === 'dark' ? '#ffffff' : '#1F2430'" stroke-width="2"/>
            <line x1="7" y1="8" x2="17" y2="8" :stroke="currentTheme === 'dark' ? '#ffffff' : '#1F2430'" stroke-width="2" stroke-linecap="round"/>
            <line x1="7" y1="12" x2="17" y2="12" :stroke="currentTheme === 'dark' ? '#ffffff' : '#1F2430'" stroke-width="2" stroke-linecap="round"/>
            <line x1="7" y1="16" x2="14" y2="16" :stroke="currentTheme === 'dark' ? '#ffffff' : '#1F2430'" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div v-if="hasNewLogError" class="error-dot"></div>
        <Transition name="tooltip">
          <div v-if="hoveredItem === 'logs'" class="tooltip">
            日志
          </div>
        </Transition>
      </div>
      <div
        class="menu-item"
        @mouseenter="hoveredItem = 'settings'"
        @mouseleave="hoveredItem = null"
        @click="handleClick('settings')"
      >
        <div class="icon-placeholder">
          <svg viewBox="0 0 24 24" fill="none">
            <polygon points="3,12 7.5,4 16.5,4 21,12 16.5,20 7.5,20" fill="none" :stroke="currentTheme === 'dark' ? '#ffffff' : '#1F2430'" stroke-width="2"/>
            <circle cx="12" cy="12" r="3.5" fill="none" :stroke="currentTheme === 'dark' ? '#ffffff' : '#1F2430'" stroke-width="2"/>
          </svg>
        </div>
        <Transition name="tooltip">
          <div v-if="hoveredItem === 'settings'" class="tooltip">
            设置
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  width: 60px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px 8px;
  box-sizing: border-box;
}

.sidebar[data-theme="dark"] {
  background-color: #1F2430;
}

.sidebar[data-theme="light"] {
  background-color: #E0E9FF;
}

.menu-top {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.menu-bottom {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.menu-item {
  position: relative;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.sidebar[data-theme="dark"] .menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.sidebar[data-theme="light"] .menu-item:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.icon-placeholder {
  width: 28px;
  height: 28px;
}

.sidebar[data-theme="dark"] .icon-placeholder {
  color: #e0e0e0;
}

.sidebar[data-theme="light"] .icon-placeholder {
  color: #1F2430;
}

.icon-placeholder svg {
  width: 100%;
  height: 100%;
}

.error-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  background-color: #ef4444;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.sidebar[data-theme="dark"] .error-dot {
  border-color: rgba(255, 255, 255, 0.1);
}

.tooltip {
  position: absolute;
  left: 54px;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  white-space: nowrap;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.sidebar[data-theme="dark"] .tooltip {
  background-color: #2d2d44;
  color: #ffffff;
}

.sidebar[data-theme="light"] .tooltip {
  background-color: #ffffff;
  color: #1F2430;
}

.tooltip-enter-active,
.tooltip-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
  transform: translateX(-4px);
}
</style>
