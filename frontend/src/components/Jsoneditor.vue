<script setup lang="ts">
import { ref, inject, type Ref } from 'vue'

type Theme = 'light' | 'dark'

const currentTheme = inject<Ref<Theme>>('theme')
const props = defineProps<{
  fileName: string
  content: string
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'update:content', value: string): void
}>()

const editorContent = ref(props.content)

function handleTabKey(event: KeyboardEvent) {
  if (event.key === 'Tab') {
    event.preventDefault()
    const textarea = event.target as HTMLTextAreaElement
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const value = textarea.value
    editorContent.value = value.substring(0, start) + '    ' + value.substring(end)
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 4
    }, 0)
  }
}

function goBack() {
  emit('back')
}
</script>

<style src="./Jsoneditor.css" scoped></style>

<template>
  <div class="json-editor" :data-theme="currentTheme">
    <div class="editor-header">
      <button
        class="back-btn"
        @click="goBack"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        <span>返回</span>
      </button>
      <span class="file-title">{{ fileName }}</span>
    </div>
    <div class="editor-container">
      <textarea
        class="text-editor"
        v-model="editorContent"
        placeholder="在此输入宏内容..."
        @keydown="handleTabKey"
        @input="emit('update:content', editorContent)"
      ></textarea>
    </div>
  </div>
</template>
