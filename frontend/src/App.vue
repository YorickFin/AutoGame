<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'

const currentView = ref('mouse')
const isMaximized = ref(false)

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
</script>

<template>
  <div class="app-container">
    <Sidebar class="sidebar" @navigate="handleNavigate" />
    <main class="content">
      <div class="title-bar">
        <div class="title">AutoGame</div>
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
              <path d="M5 5l14 14M19 5l-14 14" stroke-linecap="round" />
            </svg>
          </button>
        </div>
      </div>
      <div class="view-container">
        <h1>{{ currentView === 'mouse' ? '鼠标控制' : currentView === 'screencast' ? '手机投屏' : '设置' }}</h1>
        <p>内容区域 - {{ currentView }}</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: #1a1a2e;
}

.sidebar {
  flex: 0 0 60px;
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #0f0f1a;
}

.title-bar {
  height: 36px;
  background-color: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  cursor: default;
  user-select: none;
  -webkit-app-region: drag;
}

.title {
  color: #e0e0e0;
  font-size: 14px;
  font-weight: 500;
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
  color: #9ca3af;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.control-btn:hover {
  background-color: rgba(255, 255, 255, 0.08);
  color: #f3f4f6;
}

.close-btn:hover {
  background-color: #ef4444;
  color: #fff;
}

.control-btn svg {
  width: 14px;
  height: 14px;
  transition: transform 0.15s ease;
}

.control-btn:hover svg {
  transform: scale(1.05);
}

.view-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #e0e0e0;
}

.view-container h1 {
  font-size: 24px;
  margin-bottom: 16px;
}

.view-container p {
  font-size: 16px;
  color: #888;
}
</style>
