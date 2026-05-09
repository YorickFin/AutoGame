<script setup lang="ts">
import { ref, onMounted, inject, type Ref } from 'vue'

type Theme = 'light' | 'dark'

const currentTheme = inject<Ref<Theme>>('theme')
const macroFiles = ref<string[]>([])
const hoveredButtons = ref<Record<string, string>>({})
const isRenaming = ref(false)
const renameFileName = ref('')
const renameInputValue = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)

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

async function openFolder(fileName: string) {
  try {
    await (window as any).pywebview.api.open_folder(fileName)
  } catch (e) {
    console.error('Failed to open folder:', e)
  }
}

function renameFile(fileName: string) {
  hideTooltip(`${fileName}-rename`)
  isRenaming.value = true
  renameFileName.value = fileName
  renameInputValue.value = fileName.replace('.json', '')
  setTimeout(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  }, 100)
}

async function confirmRename() {
  if (!renameInputValue.value.trim()) return
  const newName = renameInputValue.value.trim()
  const oldName = renameFileName.value.replace('.json', '')
  if (newName === oldName) {
    closeRename()
    return
  }
  try {
    await (window as any).pywebview.api.rename_file(oldName, newName)
    await loadMacroFiles()
    closeRename()
  } catch (e) {
    console.error('Failed to rename file:', e)
  }
}

function closeRename() {
  isRenaming.value = false
  renameFileName.value = ''
  renameInputValue.value = ''
}

function handleRenameKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    confirmRename()
  } else if (event.key === 'Escape') {
    closeRename()
  }
}

async function deleteFile(fileName: string) {
  try {
    hideTooltip(`${fileName}-open`)
    hideTooltip(`${fileName}-rename`)
    hideTooltip(`${fileName}-folder`)
    hideTooltip(`${fileName}-delete`)
    await (window as any).pywebview.api.delete_file(fileName)
    await loadMacroFiles()
  } catch (e) {
    console.error('Failed to delete file:', e)
  }
}

async function createNewFile() {
  try {
    await (window as any).pywebview.api.create_new_file()
    await loadMacroFiles()
  } catch (e) {
    console.error('Failed to create new file:', e)
  }
}

onMounted(() => {
  loadMacroFiles()
})
</script>

<style src="./KeymouseControl.css" scoped></style>

<template>
  <div class="keymouse-control" :data-theme="currentTheme">
    <h1 class="section-title">项目文件</h1>
    <div class="top-button-bar">
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="createNewFile"
          @mouseenter="showTooltip('new-file', '新建文件')"
          @mouseleave="hideTooltip('new-file')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['new-file']" class="tooltip">
            {{ hoveredButtons['new-file'] }}
          </div>
        </Transition>
      </div>
      <div class="btn-wrapper">
        <button
          class="action-btn"
          @click="loadMacroFiles"
          @mouseenter="showTooltip('refresh', '刷新')"
          @mouseleave="hideTooltip('refresh')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
        </button>
        <Transition name="tooltip">
          <div v-if="hoveredButtons['refresh']" class="tooltip">
            {{ hoveredButtons['refresh'] }}
          </div>
        </Transition>
      </div>
    </div>
    <div class="scroll-container">
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

    <Transition name="fade">
      <div v-if="isRenaming" class="rename-overlay" @click="closeRename">
        <div class="rename-modal" @click.stop>
          <div class="rename-label">重命名</div>
          <input
            ref="renameInputRef"
            v-model="renameInputValue"
            type="text"
            class="rename-input"
            @keydown="handleRenameKeydown"
          />
          <div class="rename-buttons">
            <button class="rename-btn cancel-btn" @click="closeRename">取消</button>
            <button class="rename-btn confirm-btn" @click="confirmRename">确定</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
