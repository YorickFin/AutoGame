<script setup lang="ts">
import { ref, onMounted, inject, type Ref } from 'vue'

type Theme = 'light' | 'dark'

const currentTheme = inject<Ref<Theme>>('theme')
const macroFiles = ref<string[]>([])
const hoveredButtons = ref<Record<string, string>>({})

function showTooltip(key: string, text: string) {
  hoveredButtons.value[key] = text
}

function hideTooltip(key: string) {
  delete hoveredButtons.value[key]
}

async function loadMacroFiles() {
  const maxAttempts = 50
  let attempts = 0

  while (attempts < maxAttempts) {
    try {
      if ((window as any).pywebview && (window as any).pywebview.api) {
        macroFiles.value = await (window as any).pywebview.api.get_macro_files()
        return
      }
    } catch (e) {
      console.error('Failed to load macro files:', e)
    }
    attempts++
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  console.warn('Failed to load macro files after multiple attempts')
}

function openFile(fileName: string) {
  console.log('Open file:', fileName)
}

function openFolder(fileName: string) {
  console.log('Open folder for:', fileName)
}

function renameFile(fileName: string) {
  console.log('Rename file:', fileName)
}

function deleteFile(fileName: string) {
  console.log('Delete file:', fileName)
}

onMounted(() => {
  loadMacroFiles()
})
</script>

<template>
  <div class="keymouse-control" :data-theme="currentTheme">
    <div class="macro-list">
      <div v-for="file in macroFiles" :key="file" class="macro-item">
        <div class="file-section">
          <span class="file-name">{{ file }}</span>
        </div>
        <div class="button-section">
          <div class="btn-wrapper">
            <button 
              class="action-btn" 
              @click="openFile(file)" 
              @mouseenter="showTooltip(`${file}-open`, '打开文件')" 
              @mouseleave="hideTooltip(`${file}-open`)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </button>
            <Transition name="tooltip">
              <div v-if="hoveredButtons[`${file}-open`]" class="tooltip">
                {{ hoveredButtons[`${file}-open`] }}
              </div>
            </Transition>
          </div>
          <div class="btn-wrapper">
            <button 
              class="action-btn" 
              @click="renameFile(file)" 
              @mouseenter="showTooltip(`${file}-rename`, '重命名')" 
              @mouseleave="hideTooltip(`${file}-rename`)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7.5 19.5a2.121 2.121 0 0 1-3-3z"/>
              </svg>
            </button>
            <Transition name="tooltip">
              <div v-if="hoveredButtons[`${file}-rename`]" class="tooltip">
                {{ hoveredButtons[`${file}-rename`] }}
              </div>
            </Transition>
          </div>
          <div class="btn-wrapper">
            <button 
              class="action-btn" 
              @click="openFolder(file)" 
              @mouseenter="showTooltip(`${file}-folder`, '打开所在文件夹')" 
              @mouseleave="hideTooltip(`${file}-folder`)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
            </button>
            <Transition name="tooltip">
              <div v-if="hoveredButtons[`${file}-folder`]" class="tooltip">
                {{ hoveredButtons[`${file}-folder`] }}
              </div>
            </Transition>
          </div>
        </div>
        <div class="delete-section">
          <div class="btn-wrapper">
            <button 
              class="delete-btn" 
              @click="deleteFile(file)" 
              @mouseenter="showTooltip(`${file}-delete`, '删除文件')" 
              @mouseleave="hideTooltip(`${file}-delete`)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
            <Transition name="tooltip">
              <div v-if="hoveredButtons[`${file}-delete`]" class="tooltip">
                {{ hoveredButtons[`${file}-delete`] }}
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.keymouse-control {
  width: 100%;
  height: 100%;
  padding: 24px;
  box-sizing: border-box;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.keymouse-control::-webkit-scrollbar {
  display: none;
}

.macro-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.macro-item {
  position: relative;
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-radius: 12px;
  gap: 16px;
}

[data-theme="dark"] .macro-item {
  background-color: rgba(255, 255, 255, 0.05);
}

[data-theme="light"] .macro-item {
  background-color: rgba(0, 0, 0, 0.05);
}

.file-section {
  flex: 1;
  text-align: left;
}

.file-name {
  font-size: 16px;
  font-weight: 500;
}

.button-section {
  flex: 1;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.btn-wrapper {
  position: relative;
}

.delete-section {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

[data-theme="dark"] .file-name {
  color: #e0e0e0;
}

[data-theme="light"] .file-name {
  color: #1F2430;
}

.button-group {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

[data-theme="dark"] .action-btn {
  background-color: rgba(255, 255, 255, 0.1);
  color: #e0e0e0;
}

[data-theme="light"] .action-btn {
  background-color: rgba(0, 0, 0, 0.1);
  color: #1F2430;
}

.action-btn:hover {
  transform: translateY(-1px);
}

[data-theme="dark"] .action-btn:hover {
  background-color: rgba(255, 255, 255, 0.15);
}

[data-theme="light"] .action-btn:hover {
  background-color: rgba(0, 0, 0, 0.15);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

[data-theme="dark"] .delete-btn {
  background-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

[data-theme="light"] .delete-btn {
  background-color: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.delete-btn:hover {
  transform: translateY(-1px);
}

[data-theme="dark"] .delete-btn:hover {
  background-color: rgba(239, 68, 68, 0.3);
}

[data-theme="light"] .delete-btn:hover {
  background-color: rgba(239, 68, 68, 0.2);
}

.delete-btn svg {
  width: 18px;
  height: 18px;
}

.btn-wrapper .tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  white-space: nowrap;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.keymouse-control[data-theme="dark"] .btn-wrapper .tooltip {
  background-color: #2d2d44;
  color: #ffffff;
}

.keymouse-control[data-theme="light"] .btn-wrapper .tooltip {
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
  transform: translateX(-50%) translateY(4px);
}
</style>
