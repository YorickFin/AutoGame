<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, inject, type Ref } from 'vue'
import { EditorView } from '@codemirror/view'
import { EditorState, Compartment } from '@codemirror/state'
import { json } from '@codemirror/lang-json'
import { HighlightStyle, syntaxHighlighting, indentUnit } from '@codemirror/language'
import { tags } from '@lezer/highlight'
import { keymap } from '@codemirror/view'
import { defaultKeymap, indentWithTab, history, historyKeymap } from '@codemirror/commands'

const basicSetup = [
  history(),
  keymap.of([...defaultKeymap, ...historyKeymap]),
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

const keyName = ref('按键名称')
const mousePosition = ref('鼠标位置')
const pixelColor = ref('颜色获取')

const isListeningKeyName = ref(false)
const isListeningMousePosition = ref(false)
const isListeningPixelColor = ref(false)

let keyNameInterval: ReturnType<typeof setInterval> | null = null
let mousePositionInterval: ReturnType<typeof setInterval> | null = null
let pixelColorInterval: ReturnType<typeof setInterval> | null = null

const keyNameInputRef = ref<HTMLInputElement | null>(null)
const mousePositionInputRef = ref<HTMLInputElement | null>(null)
const pixelColorInputRef = ref<HTMLInputElement | null>(null)

async function startKeyNameListening() {
  if (keyNameInterval) return
  isListeningKeyName.value = true
  keyNameInterval = setInterval(async () => {
    try {
      const keyNameResult = await (window as any).pywebview.api.get_key_name()
      if (keyNameResult) {
        if (keyNameResult === 'MLeft') {
          keyName.value = keyNameResult
        }else if (keyNameResult !== keyName.value) {
          keyName.value = keyNameResult
          stopKeyNameListening()
        }
      }
    } catch (e) {
      // ignore errors during listening
    }
  }, 100)
}

function stopKeyNameListening() {
  if (keyNameInterval) {
    clearInterval(keyNameInterval)
    keyNameInterval = null
  }
  isListeningKeyName.value = false
  if (keyNameInputRef.value) {
    keyNameInputRef.value.blur()
  }
}

function onKeyNameFocus() {
  startKeyNameListening()
}

function onKeyNameBlur() {
}

function onKeyNameInput(event: Event) {
  const target = event.target as HTMLInputElement
  target.value = keyName.value
}

const editorRef = ref<HTMLDivElement | null>(null)
let editorView: EditorView | null = null
const languageCompartment = new Compartment()
const themeCompartment = new Compartment()
const editableCompartment = new Compartment()

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
    EditorState.tabSize.of(4),
    indentUnit.of('    '),
    EditorView.lineWrapping,
    editableCompartment.of([]),
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
  window.addEventListener('keydown', handleKeyPressStop)
  window.addEventListener('mousedown', handleMouseClickStop)
  window.addEventListener('blur', handleWindowBlur)
})

onUnmounted(() => {
  if (editorView) {
    editorView.destroy()
    editorView = null
  }
  stopAllListening()
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('keydown', handleKeyPressStop)
  window.removeEventListener('mousedown', handleMouseClickStop)
  window.removeEventListener('blur', handleWindowBlur)
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
      saveButtonText.value = '保存'

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

function stopAllListening() {
  if (keyNameInterval) {
    clearInterval(keyNameInterval)
    keyNameInterval = null
  }
  if (mousePositionInterval) {
    clearInterval(mousePositionInterval)
    mousePositionInterval = null
  }
  if (pixelColorInterval) {
    clearInterval(pixelColorInterval)
    pixelColorInterval = null
  }
  isListeningKeyName.value = false
  isListeningMousePosition.value = false
  isListeningPixelColor.value = false

  if (keyNameInputRef.value) {
    keyNameInputRef.value.blur()
  }
  if (mousePositionInputRef.value) {
    mousePositionInputRef.value.blur()
  }
  if (pixelColorInputRef.value) {
    pixelColorInputRef.value.blur()
  }
}

function stopMousePositionListening() {
  if (mousePositionInterval) {
    clearInterval(mousePositionInterval)
    mousePositionInterval = null
  }
  isListeningMousePosition.value = false
  if (mousePositionInputRef.value) {
    mousePositionInputRef.value.blur()
  }
}

function stopPixelColorListening() {
  if (pixelColorInterval) {
    clearInterval(pixelColorInterval)
    pixelColorInterval = null
  }
  isListeningPixelColor.value = false
  if (pixelColorInputRef.value) {
    pixelColorInputRef.value.blur()
  }
}

async function startMousePositionListening() {
  stopAllListening()
  isListeningMousePosition.value = true
  mousePositionInterval = setInterval(async () => {
    try {
      const result = await (window as any).pywebview.api.get_mouse_position()
      if (result) {
        mousePosition.value = result
      }
    } catch (e) {
      // ignore errors
    }
  }, 50)
}

async function startPixelColorListening() {
  stopAllListening()
  isListeningPixelColor.value = true
  pixelColorInterval = setInterval(async () => {
    try {
      const result = await (window as any).pywebview.api.get_pixel_color()
      if (result) {
        pixelColor.value = result
      }
    } catch (e) {
      // ignore errors
    }
  }, 50)
}

function handleKeyPressStop(_e: KeyboardEvent) {
  stopMousePositionListening()
  stopPixelColorListening()
}

function handleMouseClickStop(_e: MouseEvent) {
  stopMousePositionListening()
  stopPixelColorListening()
}

function handleWindowBlur() {
  stopMousePositionListening()
  stopPixelColorListening()
}

function goBack() {
  emit('back')
}

function disableEditor() {
  if (editorView) {
    editorView.dispatch({
      effects: editableCompartment.reconfigure([
        EditorView.editable.of(false),
      ]),
    })
  }
}

function enableEditor() {
  if (editorView) {
    editorView.dispatch({
      effects: editableCompartment.reconfigure([
        EditorView.editable.of(true),
      ]),
    })
  }
}

;(window as any).disableJsonEditor = disableEditor
;(window as any).enableJsonEditor = enableEditor
</script>

<style src="./Jsoneditor.css" scoped></style>

<template>
  <div class="json-editor" :data-theme="currentTheme">
    <div class="editor-header">
      <div class="header-line">
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
          <!-- <span class="file-title">{{ fileName }}</span> -->
        </div>
        <div class="tool-inputs">
          <input
            ref="keyNameInputRef"
            type="text"
            class="tool-input"
            :class="{ listening: isListeningKeyName }"
            v-model="keyName"
            @focus="onKeyNameFocus"
            @blur="onKeyNameBlur"
            @input.prevent="onKeyNameInput"
          />
          <input
            ref="mousePositionInputRef"
            type="text"
            class="tool-input"
            :class="{ listening: isListeningMousePosition }"
            v-model="mousePosition"
            @click="startMousePositionListening"
          />
          <input
            ref="pixelColorInputRef"
            type="text"
            class="tool-input"
            :class="{ listening: isListeningPixelColor }"
            v-model="pixelColor"
            @click="startPixelColorListening"
          />
        </div>
        <button
          class="save-btn"
          :class="{ success: saveButtonState === 'success', error: saveButtonState === 'error' }"
          @click="saveFile"
        >
          {{ saveButtonText }}
        </button>
      </div>
    </div>
    <div class="editor-container">
      <div ref="editorRef" class="codemirror-editor"></div>
    </div>
  </div>
</template>
