<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, inject, type Ref } from 'vue'
import { EditorView } from '@codemirror/view'
import { EditorState, Compartment } from '@codemirror/state'
import { json } from '@codemirror/lang-json'
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags } from '@lezer/highlight'
import { keymap } from '@codemirror/view'
import { defaultKeymap, indentWithTab } from '@codemirror/commands'

const basicSetup = [
  keymap.of(defaultKeymap),
  keymap.of([indentWithTab]),
]

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

const saveButtonText = ref('保存')
const saveButtonState = ref<'normal' | 'success' | 'error'>('normal')

const editorRef = ref<HTMLDivElement | null>(null)
let editorView: EditorView | null = null
const languageCompartment = new Compartment()
const themeCompartment = new Compartment()

const darkHighlightStyle = HighlightStyle.define([
  { tag: tags.propertyName, color: '#80CBC4' },
  { tag: tags.string, color: '#C3E88D' },
  { tag: tags.number, color: '#C3E88D' },
  { tag: tags.bool, color: '#C3E88D' },
  { tag: tags.null, color: '#C3E88D' },
  { tag: tags.separator, color: '#CDD3DE' },
  { tag: tags.squareBracket, color: '#FFD700' },
  { tag: tags.brace, color: '#DA70D6' },
])

const lightHighlightStyle = HighlightStyle.define([
  { tag: tags.propertyName, color: '#08a8c9' },
  { tag: tags.string, color: '#bf9850' },
  { tag: tags.number, color: '#bf9850' },
  { tag: tags.bool, color: '#bf9850' },
  { tag: tags.null, color: '#bf9850' },
  { tag: tags.separator, color: '#424242' },
  { tag: tags.squareBracket, color: '#e69400' },
  { tag: tags.brace, color: '#9932CC' },
])

function getExtensions() {
  const extensions = [
    basicSetup,
    languageCompartment.of(json()),
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        emit('update:content', update.state.doc.toString())
      }
    }),
  ]

  if (currentTheme?.value === 'dark') {
    extensions.push(themeCompartment.of([
      syntaxHighlighting(darkHighlightStyle),
      EditorView.theme({
                '&': {
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  color: '#e0e0e0',
                  borderRadius: '6px',
                },
                '.cm-content': {
                  fontFamily: 'Consolas, Monaco, Courier New, monospace',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  textAlign: 'left',
                  caretColor: '#ffffff',
                },
                '.cm-line': {
                  textAlign: 'left',
                },
                '.cm-gutters': {
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  borderRight: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#888',
                },
                '.cm-activeLineGutter': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '.cm-activeLine': {
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                },
                '.cm-selectionMatch': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&.cm-focused .cm-selectionBackground': {
                  backgroundColor: 'rgba(100, 150, 255, 0.3)',
                },
                '.cm-selectionBackground': {
                  backgroundColor: 'rgba(100, 150, 255, 0.2)',
                },
                '&.cm-focused .cm-cursor': {
                  borderLeftColor: '#ffffff',
                  borderLeftWidth: '2px',
                },
              }),
    ]))
  } else {
    extensions.push(themeCompartment.of([
      syntaxHighlighting(lightHighlightStyle),
      EditorView.theme({
        '&': {
          backgroundColor: 'rgba(0, 0, 0, 0.03)',
          color: '#1F2430',
          borderRadius: '6px',
        },
        '.cm-content': {
          fontFamily: 'Consolas, Monaco, Courier New, monospace',
          fontSize: '14px',
          lineHeight: '1.6',
          textAlign: 'left',
        },
        '.cm-line': {
          textAlign: 'left',
        },
        '.cm-gutters': {
          backgroundColor: 'rgba(0, 0, 0, 0.02)',
          borderRight: '1px solid rgba(0, 0, 0, 0.1)',
          color: '#888',
        },
        '.cm-activeLineGutter': {
          backgroundColor: 'rgba(0, 0, 0, 0.05)',
        },
        '.cm-activeLine': {
          backgroundColor: 'rgba(0, 0, 0, 0.03)',
        },
        '.cm-selectionMatch': {
          backgroundColor: 'rgba(100, 150, 255, 0.2)',
        },
        '&.cm-focused .cm-selectionBackground': {
          backgroundColor: 'rgba(100, 150, 255, 0.3)',
        },
        '.cm-selectionBackground': {
          backgroundColor: 'rgba(100, 150, 255, 0.2)',
        },
      }),
    ]))
  }

  return extensions
}

function handleKeydown(event: KeyboardEvent) {
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault()
    saveFile()
  }
}

onMounted(() => {
  if (editorRef.value) {
    editorView = new EditorView({
      state: EditorState.create({
        doc: props.content,
        extensions: getExtensions(),
      }),
      parent: editorRef.value,
    })
  }
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  if (editorView) {
    editorView.destroy()
    editorView = null
  }
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => props.content, (newContent) => {
  if (editorView && editorView.state.doc.toString() !== newContent) {
    editorView.dispatch({
      changes: {
        from: 0,
        to: editorView.state.doc.length,
        insert: newContent,
      },
    })
  }
})

watch(() => currentTheme?.value, () => {
  if (editorView) {
    editorView.dispatch({
      effects: themeCompartment.reconfigure(
        currentTheme?.value === 'dark'
          ? [
              syntaxHighlighting(darkHighlightStyle),
              EditorView.theme({
                '&': {
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  color: '#e0e0e0',
                  borderRadius: '6px',
                },
                '.cm-content': {
                  fontFamily: 'Consolas, Monaco, Courier New, monospace',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  textAlign: 'left',
                  caretColor: '#ffffff',
                },
                '.cm-line': {
                  textAlign: 'left',
                },
                '.cm-gutters': {
                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                  borderRight: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#888',
                },
                '.cm-activeLineGutter': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '.cm-activeLine': {
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                },
                '.cm-selectionMatch': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&.cm-focused .cm-selectionBackground': {
                  backgroundColor: 'rgba(100, 150, 255, 0.3)',
                },
                '.cm-selectionBackground': {
                  backgroundColor: 'rgba(100, 150, 255, 0.2)',
                },
                '&.cm-focused .cm-cursor': {
                  borderLeftColor: '#ffffff',
                  borderLeftWidth: '2px',
                },
              }),
            ]
          : [
              syntaxHighlighting(lightHighlightStyle),
              EditorView.theme({
                '&': {
                  backgroundColor: 'rgba(0, 0, 0, 0.03)',
                  color: '#1F2430',
                  borderRadius: '6px',
                },
                '.cm-content': {
                  fontFamily: 'Consolas, Monaco, Courier New, monospace',
                  fontSize: '14px',
                  lineHeight: '1.6',
                  textAlign: 'left',
                },
                '.cm-line': {
                  textAlign: 'left',
                },
                '.cm-gutters': {
                  backgroundColor: 'rgba(0, 0, 0, 0.02)',
                  borderRight: '1px solid rgba(0, 0, 0, 0.1)',
                  color: '#888',
                },
                '.cm-activeLineGutter': {
                  backgroundColor: 'rgba(0, 0, 0, 0.05)',
                },
                '.cm-activeLine': {
                  backgroundColor: 'rgba(0, 0, 0, 0.03)',
                },
                '.cm-selectionMatch': {
                  backgroundColor: 'rgba(100, 150, 255, 0.2)',
                },
                '&.cm-focused .cm-selectionBackground': {
                  backgroundColor: 'rgba(100, 150, 255, 0.3)',
                },
                '.cm-selectionBackground': {
                  backgroundColor: 'rgba(100, 150, 255, 0.2)',
                },
              }),
            ]
      ),
    })
  }
})

async function saveFile() {
  if (!editorView || !props.fileName) return

  saveButtonState.value = 'normal'
  saveButtonText.value = '保存'

  try {
    const currentContent = editorView.state.doc.toString()
    const result = await (window as any).pywebview.api.save_macrofile(props.fileName, currentContent)

    if (result === false) {
      saveButtonState.value = 'error'
      saveButtonText.value = '错误'
    } else {
      saveButtonState.value = 'success'
      saveButtonText.value = '已保存'

      if (result && typeof result === 'object') {
        const formattedContent = JSON.stringify(result, null, 4)
        editorView.dispatch({
          changes: {
            from: 0,
            to: editorView.state.doc.length,
            insert: formattedContent,
          },
        })
        emit('update:content', formattedContent)
      }

      setTimeout(() => {
        saveButtonState.value = 'normal'
        saveButtonText.value = '保存'
      }, 3000)
    }
  } catch (error) {
    console.error('保存失败:', error)
    saveButtonState.value = 'error'
    saveButtonText.value = '错误'
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
      <div class="header-left">
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
      <button
        class="save-btn"
        :class="{ success: saveButtonState === 'success', error: saveButtonState === 'error' }"
        @click="saveFile"
      >
        {{ saveButtonText }}
      </button>
    </div>
    <div class="editor-container">
      <div ref="editorRef" class="codemirror-editor"></div>
    </div>
  </div>
</template>
