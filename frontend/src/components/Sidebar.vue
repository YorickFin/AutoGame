<script setup lang="ts">
import { ref } from 'vue'

interface MenuItem {
  id: string
  label: string
  icon: string
}

const menuItems: MenuItem[] = [
  { id: 'mouse', label: '鼠标控制', icon: '' },
  { id: 'screencast', label: '手机投屏', icon: '' },
]

const hoveredItem = ref<string | null>(null)

const emit = defineEmits<{
  (e: 'navigate', id: string): void
}>()

function handleClick(id: string) {
  emit('navigate', id)
}
</script>

<template>
  <div class="sidebar">
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
          <svg viewBox="0 0 24 24" fill="currentColor">
            <rect x="4" y="4" width="16" height="16" rx="2" />
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
        @mouseenter="hoveredItem = 'settings'"
        @mouseleave="hoveredItem = null"
        @click="handleClick('settings')"
      >
        <div class="icon-placeholder">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" />
            <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
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
  background-color: #1a1a2e;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px 8px;
  box-sizing: border-box;
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
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.menu-item:hover {
  background-color: #16213e;
}

.icon-placeholder {
  width: 28px;
  height: 28px;
  color: #e0e0e0;
}

.icon-placeholder svg {
  width: 100%;
  height: 100%;
}

.tooltip {
  position: absolute;
  left: 54px;
  background-color: #2d2d44;
  color: #ffffff;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  white-space: nowrap;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
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
