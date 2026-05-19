<template>
  <div class="screencast-viewer" :class="{ 'fullscreen-mode': isFullscreen }" :data-theme="currentTheme" @keydown="handleKeydown">
    <div v-if="!isFullscreen" class="viewer-sidebar">
      <button class="stop-btn" @click="handleStop">
        <span>停止</span>
      </button>
    </div>
    <div ref="viewport" class="viewport">
      <div class="screen-wrapper" :style="screenStyle">
        <canvas
          ref="canvas"
          @pointerdown.prevent="onPointer(0, $event)"
          @pointermove.prevent="onPointer(2, $event)"
          @pointerup.prevent="onPointer(1, $event)"
          @pointercancel.prevent="onPointer(1, $event)"
        />
        <div class="fps-overlay" v-if="showFps">{{ fps }}</div>
        <div v-if="!session.width" class="placeholder">
          <div class="spinner"></div>
          <p>{{ statusText }}</p>
        </div>

<!-- Key Mapping Overlay -->
      <div v-if="showKeyMapping" class="key-mapping-overlay"
           @mousedown.left="onOverlayMouseDown"
           @mousemove="onOverlayMouseMove"
           @mouseup.left="onOverlayMouseUp"
           @click.right.prevent="onOverlayRightClick"
           @contextmenu.prevent
           ref="overlayRef">
        <div class="km-center-wrapper">
<div class="key-mapping-canvas" ref="kmCanvasRef" :style="screenStyle" @mousedown.left.stop="onCanvasMouseDown($event)">
          <!-- Single controls -->
          <div v-for="ctrl in controls" :key="ctrl.id"
               class="key-control"
               :class="{ listening: editingControlId === ctrl.id }"
               :style="ctrlStyle(ctrl)"
               @mousedown.left.stop="startDrag($event, ctrl)"
               @click.stop="editControl(ctrl)">
            <div class="control-circle">
              <span class="control-label" :style="ctrlLabelStyle(ctrl)">{{ ctrl.label || (editingControlId === ctrl.id ? "..." : "?") }}</span>
              <button class="control-close" @click.stop="removeControl(ctrl.id)" :style="controlCloseStyle(ctrl)">&times;</button>
            </div>
          </div>
          <!-- DPad controls -->
          <div v-for="dpad in dpads" :key="dpad.id"
               class="key-control dpad"
               :style="ctrlStyle(dpad, true)" @mousedown.left.stop="startDrag($event, dpad, 'dpad')">
            <div class="dpad-rect"></div>
            <div class="dpad-circle"></div>
            <div v-for="dir in ['up','down','left','right']" :key="dir"
                 class="dpad-key"
                 :class="{ listening: editingDpadId === dpad.id && editingDpadDir === dir }"
                 :style="getDpadKeyStyle(dpad, dir)"
                 @click.stop="editDpadKey(dpad, dir)">
              {{ dpad.keys[dir].label }}
            </div>
            <div class="resize-handle br" :style="resizeHandleStyle(dpad, 'br')" @mousedown.stop="startDpadResize($event, dpad)"></div>
            <div class="resize-handle tr" :style="resizeHandleStyle(dpad, 'tr')" @mousedown.stop="startDpadResize($event, dpad)"></div>
            <div class="resize-handle bl" :style="resizeHandleStyle(dpad, 'bl')" @mousedown.stop="startDpadResize($event, dpad)"></div>
            <div class="resize-handle tl" :style="resizeHandleStyle(dpad, 'tl')" @mousedown.stop="startDpadResize($event, dpad)"></div>
            <button class="control-close" @click.stop="removeControl(dpad.id)" :style="{ ...controlCloseStyle(dpad), position: 'absolute', zIndex: 10 }">&times;</button>
          </div>
          <!-- Swipe controls -->
          <div v-for="swp in swipes" :key="swp.id"
               class="key-control"
               :class="{ listening: editingControlId === swp.id }"
               :style="ctrlStyle(swp)"
               @mousedown.left.stop="startDrag($event, swp, 'swipe')"
               @click.stop="editControl(swp)">
            <div class="control-circle">
              <span class="control-label" :style="ctrlLabelStyle(swp)">{{ swp.label || "滑动" }}</span>
              <button class="control-close" @click.stop="removeControl(swp.id)" :style="controlCloseStyle(swp)">&times;</button>
            </div>
          </div>
          <!-- Swipe recording preview -->
          <svg v-if="isRecordingSwipe && swipePoints.length > 1" class="swipe-preview">
            <polyline :points="swipePoints.map(p => (p.x * kmCanvasWidth) + ',' + (p.y * kmCanvasHeight)).join(' ')"></polyline>
          </svg>

          <!-- Last recorded swipe path (persistent) -->
          <svg v-if="lastSwipePath.length > 1" class="swipe-preview saved-swipe">
            <polyline :points="lastSwipePath.map(p => (p.x * kmCanvasWidth) + ',' + (p.y * kmCanvasHeight)).join(' ')"></polyline>
          </svg>

          <!-- Saved swipe controls paths -->
          <svg v-for="swp in swipes" :key="'path-' + swp.id" v-show="swp.path && swp.path.length > 1" class="swipe-preview saved-swipe">
            <polyline :points="swp.path.map((p: any) => (p.x * kmCanvasWidth) + ',' + (p.y * kmCanvasHeight)).join(' ')"></polyline>
          </svg>
        </div>
</div>
        <!-- Context menu -->
        <div v-if="contextMenu.show" class="context-menu"
             :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }">
          <div @click="createDirectionKey">方向键位(WASD)</div>
          <div @click="startSwipeRecording">滑动键位</div>
        </div>
      </div>
</div>

    </div>
    <div v-if="showKeyMapping && !isFullscreen" class="key-mapping-sidebar">
      <div class="km-file-header">
        <span>键位文件</span>
        <button @click="createNewKeyMapping" title="新建">+</button>
      </div>
      <div class="km-files">
        <div v-for="f in keyMappingFiles" :key="f"
             class="km-file-item"
             :class="{ active: f === currentFile }"
             @click="switchFile(f)">
          <template v-if="renamingFile === f">
            <input v-model="renameInput" @blur="doRename" @keyup.enter="doRename" ref="renameInputRef" />
          </template>
          <template v-else>
            <span class="km-file-name">{{ f }}</span>
            <div class="km-file-actions">
              <button @click.stop="startRename(f)" title="重命名">&#9998;</button>
              <button @click.stop="deleteFile(f)" title="删除">&times;</button>
            </div>
          </template>
        </div>
      </div>
      <div class="km-actions">
        <button class="km-btn close" @click="closeKeyMapping">关闭</button>
      </div>
    </div>
    <div v-if="!isFullscreen" class="viewer-sidebar viewer-sidebar-right">
      <div class="sidebar-top">
        <div class="btn-wrapper">
          <button
            class="action-btn"
            @click="toggleKeyMapping"
            @mouseenter="showTooltip('scrcpy-expand-screen', '键位映射')"
            @mouseleave="hideTooltip('scrcpy-expand-screen')"
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
            @click="scrcpyVolumeUp"
            @mouseenter="showTooltip('scrcpy-vol-up', '音量+')"
            @mouseleave="hideTooltip('scrcpy-vol-up')"
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
            @click="scrcpyVolumeDown"
            @mouseenter="showTooltip('scrcpy-vol-down', '音量-')"
            @mouseleave="hideTooltip('scrcpy-vol-down')"
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
            @click="toggleScrcpyFullscreen"
            @mouseenter="showTooltip('scrcpy-fullscreen', isFullscreen ? '退出全屏' : '全屏')"
            @mouseleave="hideTooltip('scrcpy-fullscreen')"
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
            @click="toggleShowFps"
            @mouseenter="hoveredButtons['toggle-fps'] = showFps ? '隐藏帧率' : '显示帧率'"
            @mouseleave="hideTooltip('toggle-fps')"
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
            @click="scrcpyBack"
            @mouseenter="showTooltip('scrcpy-back', '返回')"
            @mouseleave="hideTooltip('scrcpy-back')"
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
            @click="scrcpySwitchApp"
            @mouseenter="showTooltip('scrcpy-switch-app', '多应用')"
            @mouseleave="hideTooltip('scrcpy-switch-app')"
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
            @click="scrcpyHome"
            @mouseenter="showTooltip('scrcpy-home', '主页')"
            @mouseleave="hideTooltip('scrcpy-home')"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted, onBeforeUnmount, nextTick, type Ref } from "vue"
import "./ScreenCastView.css"

type Theme = "light" | "dark"

const currentTheme = inject<Ref<Theme>>("theme")

const props = defineProps<{
  connectionMode: "usb" | "wireless"
}>()

const emit = defineEmits<{
  (e: "back"): void
  (e: "fullscreen-change", isFull: boolean): void
}>()

const keyNameMap: Record<string, string> = {
  "Numpad0": "N0",
  "Numpad1": "N1",
  "Numpad2": "N2",
  "Numpad3": "N3",
  "Numpad4": "N4",
  "Numpad5": "N5",
  "Numpad6": "N6",
  "Numpad7": "N7",
  "Numpad8": "N8",
  "Numpad9": "N9",
  "CapsLock": "CLk",
  "LShift": "LSFT",
  "RShift": "RSFT",
  "Insert": "INS",
  "Delete": "DEL",
  "ScrollLock": "SLK",
  "VolumeDown": "VOLDW",
  "VolumeUp": "VOLUP",
  "VolumeMute": "MUTE",
  "LaunchApp2": "App2",
}

function getKeyLabel(key: string): string {
  return keyNameMap[key] || key
}

// ------------------------------------------------------------------ #
// Screen / canvas state
// ------------------------------------------------------------------ #

const canvas = ref<HTMLCanvasElement | null>(null)
const viewport = ref<HTMLElement | null>(null)
const viewportSize = ref({ width: 0, height: 0 })
const session = ref({ width: 0, height: 0 })
const fps = ref(0)
const showFps = ref(true)
const isKeyMappingActive = ref(false)

const statusText = ref("Connecting...")
const status = ref<{ running: boolean; deviceName?: string | null; error?: string | null }>({
  running: false,
})

const hoveredButtons = ref<Record<string, string>>({})
const isFullscreen = ref(false)

// ------------------------------------------------------------------ #
// Computed
// ------------------------------------------------------------------ #

const screenStyle = computed(() => {
  if (!session.value.width || !session.value.height) return {}
  const padding = 0
  const aw = Math.max(1, viewportSize.value.width - padding)
  const ah = Math.max(1, viewportSize.value.height - padding)
  const scale = Math.min(aw / session.value.width, ah / session.value.height)
  return {
    width: `${Math.floor(session.value.width * scale)}px`,
    height: `${Math.floor(session.value.height * scale)}px`,
  }
})

// ------------------------------------------------------------------ #
// Tooltip helpers
// ------------------------------------------------------------------ #

function showTooltip(key: string, text: string) {
  hoveredButtons.value[key] = text
}

function hideTooltip(key: string) {
  delete hoveredButtons.value[key]
}

// ------------------------------------------------------------------ #
// Control helpers
// ------------------------------------------------------------------ #

function scrcpyVolumeUp() {
  callApi("scrcpy_volume_up").catch(() => {})
}

function scrcpyVolumeDown() {
  callApi("scrcpy_volume_down").catch(() => {})
}

function toggleScrcpyFullscreen() {
  isFullscreen.value = !isFullscreen.value
  emit('fullscreen-change', isFullscreen.value)

  // 调用 pywebview 的窗口最大化/还原功能
  if ((window as any).pywebview && (window as any).pywebview.api) {
    (window as any).pywebview.api.toggle_maximize()
  }
}

async function toggleShowFps() {
  const newShowFps = !showFps.value

  delete hoveredButtons.value['toggle-fps']
  showFps.value = newShowFps

  await nextTick()
  hoveredButtons.value['toggle-fps'] = newShowFps ? '隐藏帧率' : '显示帧率'

  if (!(window as any).pywebview?.api) {
    console.warn('pywebview API not available')
    return
  }

  try {
    const config = await callApi("get_config_file")
    if (!config.screencast) config.screencast = {}
    config.screencast.showFps = newShowFps
    await callApi("save_config_file", config)
  } catch (e) {
    if (e instanceof Error && e.message.includes('ObjectDisposedException')) {
      console.warn('Window is closing, skipping save')
    } else {
      console.error('Failed to save showFps config:', e)
    }
  }
}

function scrcpyBack() {
  callApi("scrcpy_back").catch(() => {})
}

function scrcpySwitchApp() {
  callApi("scrcpy_switch_app").catch(() => {})
}

function scrcpyHome() {
  callApi("scrcpy_home").catch(() => {})
}

async function handleStop() {
  await teardownKeyCapture()

  stopConnection()
  emit("back")
}

// ------------------------------------------------------------------ #
// Video decoder state
// ------------------------------------------------------------------ #

let videoDecoder: VideoDecoder | null = null
let audioContext: AudioContext | null = null
let audioScheduleEnd: number = 0
const MAX_AUDIO_SCHEDULE_HEAD = 0.15  // 150ms max schedule ahead
const AUDIO_SCHEDULE_OFFSET = 0.005  // 10ms minimum lookahead
let videoConfigured = false
let pollTimer = 0
let fpsTimer = 0
let framesThisSecond = 0
let resizeObserver: ResizeObserver | null = null

let kmResizeObserver: ResizeObserver | null = null


// ------------------------------------------------------------------ #
// API helpers
// ------------------------------------------------------------------ #

function ensureApi() {
  if (!(window as any).pywebview?.api) throw new Error("pywebview API is not available")
}

async function callApi(method: string, ...args: any[]): Promise<any> {
  ensureApi()
  return await (window as any).pywebview.api[method](...args)
}

function base64ToBytes(payload: string) {
  return Uint8Array.from(atob(payload), c => c.charCodeAt(0))
}

// ------------------------------------------------------------------ #
// Connection
// ------------------------------------------------------------------ #

async function startConnection() {
  try {
    statusText.value = "Connecting..."
    const config = await callApi("get_config_file")
    const scConfig = config.screencast || {}
    if (scConfig.showFps !== undefined) showFps.value = scConfig.showFps

    let resolvedSerial: string | undefined

    if (props.connectionMode === "wireless") {
      statusText.value = "Switching to wireless..."
      const result = await callApi("scrcpy_switch_to_wireless")
      if (result.ok) {
        resolvedSerial = result.serial
      } else {
        status.value = { running: false, error: result.error }
        statusText.value = result.error || "Wireless switch failed"
        return
      }
    } else {
      // USB mode - auto-discover or use serial
      const serial = await callApi("scrcpy_discover_usb_serial")
      resolvedSerial = serial || undefined
    }

    status.value = await callApi("scrcpy_start", resolvedSerial || null, scConfig)
    if (status.value.running) {
      statusText.value = `Connected to ${status.value.deviceName || "device"}`
      startPolling()
      await loadKeyMappingOnConnect()
    } else {
      statusText.value = status.value.error || "Connection failed"
    }
  } catch (e) {
    statusText.value = e instanceof Error ? e.message : String(e)
  }
}

async function stopConnection() {
  stopPolling()
  closeDecoders()
  try {
    await callApi("scrcpy_stop")
  } catch {
    // ignore
  }
  status.value = { running: false }
}

// ------------------------------------------------------------------ #
// Polling
// ------------------------------------------------------------------ #

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    if (!status.value.running) return
    try {
      const events = await callApi("scrcpy_poll_events", 40)
      for (const event of events) handleEvent(event)
    } catch {
      // ignore
    }
  }, 16)
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = 0
  }
}

type StreamEvent = {
  kind: "session" | "video" | "audio" | "error"
  codec?: string | null
  width?: number
  height?: number
  pts?: number | null
  config?: boolean
  keyFrame?: boolean
  payload?: string
  message?: string
  clientResized?: boolean
}

function handleEvent(event: StreamEvent) {
  if (event.kind === "session") {
    session.value = { width: event.width || 0, height: event.height || 0 }
    resizeCanvas()
    return
  }
  if (event.kind === "video" && event.payload) {
    framesThisSecond++
    decodeVideo(event)
    return
  }
  if (event.kind === "audio" && event.payload) {
    playAudio(event.payload)
    return
  }
}

// ------------------------------------------------------------------ #
// Video decoding
// ------------------------------------------------------------------ #

function decodeVideo(event: StreamEvent) {
  if (!("VideoDecoder" in window)) return
  if (event.codec !== "h264") return

  const data = base64ToBytes(event.payload || "")

  if (!videoDecoder) {
    videoDecoder = new VideoDecoder({
      output(frame) {
        const cvs = canvas.value
        if (!cvs) {
          frame.close()
          return
        }
        const ctx = cvs.getContext("2d")
        if (ctx) {
          ctx.drawImage(frame, 0, 0, cvs.width, cvs.height)
        }
        frame.close()
      },
      error(e) {
        console.error("VideoDecoder error:", e.message)
      },
    })
  }

  if (!videoConfigured) {
    videoDecoder.configure({
      codec: "avc1.42E01E",
      optimizeForLatency: true,
      avc: { format: "annexb" },
    } as VideoDecoderConfig)
    videoConfigured = true
  }

  // Skip delta frames until a key frame arrives after configure
  if (!event.keyFrame && !videoConfigured) return

  const chunk = new EncodedVideoChunk({
    type: event.keyFrame ? "key" : "delta",
    timestamp: event.pts || performance.now() * 1000,
    data,
  })

  try {
    videoDecoder.decode(chunk)
  } catch (e) {
    console.error("Decode error:", e)
  }
}

function playAudio(payload: string) {
  const data = base64ToBytes(payload || "")
  if (!data.length) return

  if (!audioContext) {
    audioContext = new AudioContext({ sampleRate: 48000 })
    audioScheduleEnd = audioContext.currentTime
  }

  const frameCount = Math.floor(data.length / 4)
  if (frameCount <= 0) return

  const buffer = audioContext.createBuffer(2, frameCount, 48000)
  const ch0 = buffer.getChannelData(0)
  const ch1 = buffer.getChannelData(1)

  for (let j = 0; j < frameCount; j++) {
    const offset = j * 4
    ch0[j] = audioSample(data[offset], data[offset + 1])
    ch1[j] = audioSample(data[offset + 2], data[offset + 3])
  }

  const source = audioContext.createBufferSource()
  source.buffer = buffer
  source.connect(audioContext.destination)

  // Use current time as base, but ensure gapless by respecting audioScheduleEnd
  const now = audioContext.currentTime
  // If audioScheduleEnd has drifted too far ahead (e.g. after tab switch), reset it
  if (audioScheduleEnd - now > MAX_AUDIO_SCHEDULE_HEAD) {
    audioScheduleEnd = now + AUDIO_SCHEDULE_OFFSET
  }
  const scheduledTime = Math.max(now + AUDIO_SCHEDULE_OFFSET, audioScheduleEnd)
  source.start(scheduledTime)
  audioScheduleEnd = scheduledTime + buffer.duration
}

function audioSample(lo: number, hi: number) {
  const val = (hi << 8) | lo
  return (val >= 32768 ? val - 65536 : val) / 32768
}

function closeDecoders() {
  if (videoDecoder) {
    videoDecoder.close()
    videoDecoder = null
  }
  videoConfigured = false
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
}

// ------------------------------------------------------------------ #
// Canvas / resize
// ------------------------------------------------------------------ #

function resizeCanvas() {
  const cvs = canvas.value
  if (!cvs || !session.value.width || !session.value.height) return
  cvs.width = session.value.width
  cvs.height = session.value.height
}


// ------------------------------------------------------------------ #
// Touch / pointer
// ------------------------------------------------------------------ #

async function onPointer(action: number, event: PointerEvent) {
  if (!status.value.running || !session.value.width || !session.value.height || !canvas.value) return

  // Only send ACTION_MOVE when a button is actually held down
  // This avoids flooding the scrcpy control stream with spurious moves
  // when the user is just hovering the mouse over the canvas.
  if (action === 2 && event.buttons === 0) return

  const rect = canvas.value.getBoundingClientRect()
  const x = Math.max(0, Math.min(session.value.width, Math.round(((event.clientX - rect.left) / rect.width) * session.value.width)))
  const y = Math.max(0, Math.min(session.value.height, Math.round(((event.clientY - rect.top) / rect.height) * session.value.height)))

  if (action === 0) canvas.value.setPointerCapture(event.pointerId)
  if (action === 1) canvas.value.releasePointerCapture(event.pointerId)

  try {
    await callApi("scrcpy_send_touch", action, x, y, session.value.width, session.value.height)
  } catch {
    // ignore
  }
}

// ------------------------------------------------------------------ #
// Lifecycle
// ------------------------------------------------------------------ #



// ------------------------------------------------------------------ #
// Key Mapping State
// ------------------------------------------------------------------ #

const showKeyMapping = ref(false)
const keyMappingFiles = ref<string[]>([])
const currentFile = ref("")
const controls = ref<any[]>([])
const dpads = ref<any[]>([])
const swipes = ref<any[]>([])
const contextMenu = ref({ show: false, x: 0, y: 0 })
const editingControlId = ref<string | null>(null)
const editingDpadId = ref<string | null>(null)
const editingDpadDir = ref<string | null>(null)
const isRecordingSwipe = ref(false)
const pendingSwipe = ref(false)
const swipePoints = ref<{x:number,y:number,delayMs:number}[]>([])
const swipeStartTime = ref(0)
const lastSwipePath = ref<{x:number,y:number,delayMs:number}[]>([])
const kmCanvasWidth = ref(0)
const kmCanvasHeight = ref(0)

function updateKmCanvasSize() {
  if (!kmCanvasRef.value) return
  const rect = kmCanvasRef.value.getBoundingClientRect()
  kmCanvasWidth.value = rect.width
  kmCanvasHeight.value = rect.height
}

function toNormalizedCoords(clientX: number, clientY: number) {
  if (!canvas.value) return { x: 0, y: 0 }
  const rect = canvas.value.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return { x: 0, y: 0 }
  return {
    x: (clientX - rect.left) / rect.width,
    y: (clientY - rect.top) / rect.height,
  }
}

const renamingFile = ref<string | null>(null)
const renameInput = ref("")
const renameInputRef = ref<HTMLInputElement | null>(null)
const kmCanvasRef = ref<HTMLElement | null>(null)
let dragTarget: any = null
let dragOffsetX = 0
let dragOffsetY = 0
let resizeTarget: any = null
let resizeStartSize = 0
let resizeStartMouse = { x: 0, y: 0 }

function ctrlStyle(item: any, isDpad = false) {
  if (!kmCanvasRef.value) return {}
  const rect = kmCanvasRef.value.getBoundingClientRect()
  const pw = rect.width, ph = rect.height
  if (pw <= 0 || ph <= 0) return {}
  if (isDpad) {
    const s = (item.size || 0.06) * pw
    return { left: (item.x*pw)+"px", top: (item.y*ph)+"px", width: s+"px", height: s+"px" }
  }
  const sw = session.value.width || 1920
  const r = (item.radius || 25) * (pw/sw)
  const fontSize = r * 0.5
  return { left: (item.x*pw)+"px", top: (item.y*ph)+"px", width: (r*2)+"px", height: (r*2)+"px", fontSize: fontSize+"px" }
}

function ctrlLabelStyle(item: any) {
  if (!kmCanvasRef.value) return {}
  const rect = kmCanvasRef.value.getBoundingClientRect()
  const pw = rect.width
  if (pw <= 0) return {}
  const sw = session.value.width || 1920
  const r = (item.radius || 25) * (pw/sw)
  const fontSize = r * 0.6
  return { fontSize: fontSize+"px" }
}

function controlCloseStyle(item: any) {
  if (!kmCanvasRef.value) return {}
  const rect = kmCanvasRef.value.getBoundingClientRect()
  const pw = rect.width
  if (pw <= 0) return {}
  const sw = session.value.width || 1920
  const r = (item.radius || 25) * (pw/sw)
  const btnSize = r * 0.9
  const fontSize = btnSize * 0.9
  return {
    width: btnSize + "px",
    height: btnSize + "px",
    fontSize: fontSize + "px",
    top: (-btnSize / 2.5) + "px",
    right: (-btnSize / 2.5) + "px"
  }
}

function getDpadKeyStyle(dpad: any, dir: string) {
  if (!canvas.value) return {}
  const rect = canvas.value.getBoundingClientRect()
  const pw = rect.width
  if (pw <= 0) return {}
  const s = (dpad.size || 0.06) * pw, r = s/2, o = r*0.6
  const keySize = r * 0.4
  const fontSize = keySize * 0.55
  const angles: Record<string, number> = {up:-90,down:90,left:180,right:0}
  const a = (angles[dir] ?? 0) * Math.PI/180
  return { left: (r+o*Math.cos(a)-keySize/2)+"px", top: (r+o*Math.sin(a)-keySize/2)+"px", width: keySize+"px", height: keySize+"px", lineHeight: keySize+"px", textAlign:"center" as const, fontSize: fontSize+"px", position:"absolute" as const, cursor:"pointer", background:"rgba(255,255,255,0.2)", borderRadius: (keySize*0.2)+"px", color:"#fff", userSelect:"none" as const }
}

function resizeHandleStyle(item: any, position: string) {
  if (!canvas.value) return {}
  const rect = canvas.value.getBoundingClientRect()
  const pw = rect.width
  if (pw <= 0) return {}
  const s = (item.size || 0.06) * pw
  const handleSize = Math.max(10, s * 0.08)
  const offset = -handleSize / 2
  const styles: Record<string, string> = {
    width: handleSize + "px",
    height: handleSize + "px"
  }
  if (position.includes('t')) styles.top = offset + "px"
  if (position.includes('b')) styles.bottom = offset + "px"
  if (position.includes('l')) styles.left = offset + "px"
  if (position.includes('r')) styles.right = offset + "px"
  return styles
}
function controlId(prefix: string): string {
  return prefix + "_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6)
}

// ---- Overlay toggle ----
function toggleKeyMapping() {
  showKeyMapping.value = !showKeyMapping.value
  if (showKeyMapping.value) {
    nextTick(() => {
      if (kmCanvasRef.value && !kmResizeObserver) {
        kmResizeObserver = new ResizeObserver(() => { updateKmCanvasSize() })
        kmResizeObserver.observe(kmCanvasRef.value)
      }
      updateKmCanvasSize()
    })
  } else {
    if (kmResizeObserver) {
      kmResizeObserver.disconnect()
      kmResizeObserver = null
    }
    closeKeyMapping()
  }
}

// ---- File management ----
async function loadKeyMappingOnConnect() {
  try {
    const config = await callApi("get_config_file")
    const savedFileName = config.keyMappingFile

    keyMappingFiles.value = await callApi("get_key_mapping_files")

    if (savedFileName && keyMappingFiles.value.includes(savedFileName)) {
      await switchFile(savedFileName)
    } else if (keyMappingFiles.value.length > 0) {
      await switchFile(keyMappingFiles.value[0])
      await saveSelectedKeyMappingFile(keyMappingFiles.value[0])
    } else {
      const newFileName = await callApi("create_key_mapping_file")
      if (newFileName) {
        keyMappingFiles.value.push(newFileName)
        await switchFile(newFileName)
        await saveSelectedKeyMappingFile(newFileName)
      }
    }
  } catch (e) {
    console.error("Failed to load key mapping on connect:", e)
  }
}

async function saveSelectedKeyMappingFile(fileName: string) {
  try {
    const config = await callApi("get_config_file")
    config.keyMappingFile = fileName
    await callApi("save_config_file", config)
  } catch (e) {
    console.error("Failed to save key mapping file selection:", e)
  }
}

async function switchFile(name: string, skipSave = false) {
  if (renamingFile.value) return
  if (!skipSave) {
    await saveCurrentMapping()
  }
  currentFile.value = name

  editingControlId.value = null
  editingDpadId.value = null
  editingDpadDir.value = null

  lastSwipePath.value = []

  try {
    const data = await callApi("load_key_mapping_file", name)
    if (data) {
      controls.value = (data.controls || []).map((c: any) => ({ ...c }))
      dpads.value = (data.dpad || []).map((d: any) => ({ ...d }))
      swipes.value = (data.swipes || []).map((s: any) => ({ ...s }))
    } else {
      controls.value = []
      dpads.value = []
      swipes.value = []
    }
    await callApi("apply_key_mapping", name)
    isKeyMappingActive.value = true
    await saveSelectedKeyMappingFile(name)
    if (showKeyMapping.value) {
      nextTick(() => {
        updateKmCanvasSize()
      })
    }
  } catch (e) {
    controls.value = []
    dpads.value = []
    swipes.value = []
    console.error("Failed to load key mapping:", e)
  }
}

async function saveCurrentMapping() {
  if (!currentFile.value) return
  const data = {
    version: 1,
    name: currentFile.value,
    controls: controls.value.map(c => ({ id: c.id, type: "single", key: c.key, label: c.label, x: c.x, y: c.y, radius: c.radius })),
    dpad: dpads.value.map(d => ({ id: d.id, type: "dpad", x: d.x, y: d.y, size: d.size, keys: d.keys })),
    swipes: swipes.value.map(s => ({ id: s.id, type: "swipe", label: s.label, key: s.key || "", x: s.x, y: s.y, radius: s.radius, path: s.path })),
  }
  try {
    await callApi("save_key_mapping_file", currentFile.value, data)
    await callApi("apply_key_mapping", currentFile.value)
    isKeyMappingActive.value = true
  } catch (e) {
    console.error("Failed to save key mapping:", e)
  }
}

async function createNewKeyMapping() {
  try {
    const name = await callApi("create_key_mapping_file")
    if (name) {
      keyMappingFiles.value.push(name)
      await switchFile(name)
    }
  } catch (e) {
    console.error("Failed to create key mapping:", e)
  }
}

function startRename(name: string) {
  renamingFile.value = name
  renameInput.value = name
  nextTick(() => renameInputRef.value?.focus())
}

async function doRename() {
  if (!renamingFile.value || !renameInput.value.trim()) {
    renamingFile.value = null
    return
  }
  const oldName = renamingFile.value
  const newName = renameInput.value.trim()
  renamingFile.value = null
  if (oldName === newName) return
  try {
    await callApi("rename_key_mapping_file", oldName, newName)
    const idx = keyMappingFiles.value.indexOf(oldName)
    if (idx >= 0) keyMappingFiles.value[idx] = newName
    if (currentFile.value === oldName) currentFile.value = newName
  } catch (e) {
    console.error("Failed to rename:", e)
  }
}

async function deleteFile(name: string) {
  try {
    await callApi("delete_key_mapping_file", name)
    keyMappingFiles.value = keyMappingFiles.value.filter(f => f !== name)
    if (currentFile.value === name) {
      currentFile.value = keyMappingFiles.value[0] || ""
      controls.value = []
      dpads.value = []
      swipes.value = []
      lastSwipePath.value = []
      editingControlId.value = null
      editingDpadId.value = null
      editingDpadDir.value = null
      if (currentFile.value) await switchFile(currentFile.value, true)
    }
  } catch (e) {
    console.error("Failed to delete:", e)
  }
}

// ---- Canvas interactions ----
function onCanvasMouseDown(e: MouseEvent) {
  if (!kmCanvasRef.value) return
  contextMenu.value.show = false
  if (pendingSwipe.value) {
    pendingSwipe.value = false
    isRecordingSwipe.value = true
    swipePoints.value = []
    const pos = toNormalizedCoords(e.clientX, e.clientY)
    swipePoints.value = [{ x: pos.x, y: pos.y, delayMs: 0 }]
    swipeStartTime.value = Date.now()
    return
  }
  if (isRecordingSwipe.value) return
  const pos = toNormalizedCoords(e.clientX, e.clientY)

  const ctrl = {
    id: controlId("ctrl"),
    key: "",
    label: "",
    x: pos.x, y: pos.y,
    radius: 12,
  }
  controls.value.push(ctrl)
  editingControlId.value = ctrl.id
  setupKeyCapture()
}

function onOverlayRightClick(e: MouseEvent) {
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY }
}

function createDirectionKey() {
  contextMenu.value.show = false
  if (!kmCanvasRef.value) return
  const norm = toNormalizedCoords(contextMenu.value.x, contextMenu.value.y)
  const sizeNorm = 60 / (session.value.width || 1920)
  const dpad = {
    id: controlId("dpad"),
    x: norm.x, y: norm.y,
    size: sizeNorm,
    keys: {
      up: { key: "W", label: "W" },
      down: { key: "S", label: "S" },
      left: { key: "A", label: "A" },
      right: { key: "D", label: "D" },
    }
  }
  dpads.value.push(dpad)
  autoSave()
}

function startSwipeRecording() {
  contextMenu.value.show = false
  pendingSwipe.value = true
  updateKmCanvasSize()
}

function onOverlayMouseDown() {
  // Handled by onCanvasMouseDown
}

function onOverlayMouseMove(e: MouseEvent) {
  if (isRecordingSwipe.value && swipeStartTime.value > 0 && kmCanvasRef.value) {
    const pos = toNormalizedCoords(e.clientX, e.clientY)
    const x = pos.x
    const y = pos.y
    const delay = Date.now() - swipeStartTime.value
    const last = swipePoints.value[swipePoints.value.length - 1]
    // Throttle: only record if moved > 5px or 30ms passed
    if (!last || Math.hypot(x - last.x, y - last.y) > 5 || delay - (last.delayMs || 0) > 30) {
      swipePoints.value.push({ x, y, delayMs: delay })
    }
  }

  // Drag handling (normalized coords)
  if (dragTarget) {
    if (!kmCanvasRef.value) return
    const norm = toNormalizedCoords(e.clientX, e.clientY)
    const dx = (norm.x - dragOffsetX) - dragTarget.x
    const dy = (norm.y - dragOffsetY) - dragTarget.y
    dragTarget.x = Math.max(0, Math.min(1, norm.x - dragOffsetX))
    dragTarget.y = Math.max(0, Math.min(1, norm.y - dragOffsetY))
    if (dragTarget.path && Array.isArray(dragTarget.path)) {
      dragTarget.path.forEach((p: any) => {
        p.x += dx
        p.y += dy
      })
    }
  }
}

function onOverlayMouseUp(e: MouseEvent) {
  if (isRecordingSwipe.value && swipePoints.value.length > 0 && kmCanvasRef.value) {
    isRecordingSwipe.value = false
    const pos = toNormalizedCoords(e.clientX, e.clientY)
    const ex = pos.x
    const ey = pos.y
    const lastDelay = Date.now() - swipeStartTime.value
    const lastPt = swipePoints.value[swipePoints.value.length - 1]
    if (!lastPt || lastPt.x !== ex || lastPt.y !== ey) {
      swipePoints.value.push({ x: ex, y: ey, delayMs: lastDelay })
    }
    lastSwipePath.value = swipePoints.value.map(p => ({ ...p }))
    const swp = {
      id: controlId("swp"),
      label: "",
      key: "",
      x: ex, y: ey,
      radius: 12,
      path: lastSwipePath.value,
    }
    swipes.value.push(swp)
    editingControlId.value = swp.id
    setupKeyCapture()
    swipePoints.value = []
    swipeStartTime.value = 0
  }

  if (dragTarget) {
    dragTarget = null
    autoSave()
  }
  // cleanup by onResizeMouseUp
  resizeTarget = null
}

function startDrag(e: MouseEvent, ctrl: any, _type = "single") {
  if (!kmCanvasRef.value) return
  if (editingControlId.value) return
  const norm = toNormalizedCoords(e.clientX, e.clientY)
  dragTarget = ctrl
  dragOffsetX = norm.x - ctrl.x
  dragOffsetY = norm.y - ctrl.y
}

function startDpadResize(e: MouseEvent, dpad: any) {
  resizeTarget = dpad
  resizeStartSize = dpad.size
  resizeStartMouse = { x: e.clientX, y: e.clientY }
  document.addEventListener('mousemove', onResizeMouseMove)
  document.addEventListener('mouseup', onResizeMouseUp)
}

function onResizeMouseMove(e: MouseEvent) {
  if (!resizeTarget || !kmCanvasRef.value) return
  const rect = kmCanvasRef.value.getBoundingClientRect()
  const dx = (e.clientX - resizeStartMouse.x) / rect.width
  const dy = (e.clientY - resizeStartMouse.y) / rect.height
  const delta = Math.max(Math.abs(dx), Math.abs(dy)) * (dx + dy >= 0 ? 1 : -1)
  const minSize = 15 / (session.value.width || 1920)
  const maxSize = 0.5
  resizeTarget.size = Math.max(minSize, Math.min(maxSize, resizeStartSize + delta))
}

function onResizeMouseUp() {
  resizeTarget = null
  document.removeEventListener('mousemove', onResizeMouseMove)
  document.removeEventListener('mouseup', onResizeMouseUp)
  autoSave()
}

function editControl(ctrl: any) {
  if (editingControlId.value) return
  editingControlId.value = ctrl.id
  setupKeyCapture()
}

function editDpadKey(dpad: any, dir: string) {
  if (editingControlId.value) return
  editingDpadId.value = dpad.id
  editingDpadDir.value = dir
  setupKeyCapture()
}

function removeControl(id: string) {
  controls.value = controls.value.filter(c => c.id !== id)
  dpads.value = dpads.value.filter(d => d.id !== id)
  const removedSwipe = swipes.value.find(s => s.id === id)
  swipes.value = swipes.value.filter(s => s.id !== id)
  if (removedSwipe && lastSwipePath.value.length > 0) {
    const lastPathStr = JSON.stringify(lastSwipePath.value)
    const removedPathStr = JSON.stringify(removedSwipe.path)
    if (lastPathStr === removedPathStr) {
      lastSwipePath.value = []
    }
  }
  autoSave()
}

// ---- DPad key position calculation ----


// ---- Auto-save ----
let autoSaveTimer = 0
function autoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = window.setTimeout(() => {
    saveCurrentMapping()
  }, 500)
}

// ---- Key capture via backend polling ----
let keyPollTimer: number | null = null

async function setupKeyCapture() {
  await callApi("start_key_listener")
  if (keyPollTimer) {
    clearInterval(keyPollTimer)
  }
  keyPollTimer = window.setInterval(async () => {
    try {
      const result = await callApi("get_pressed_key")
      const key = result.key
      if (key) {
        await processCapturedKey(key)
        await callApi("stop_key_listener")
        if (keyPollTimer) {
          clearInterval(keyPollTimer)
          keyPollTimer = null
        }
      }
    } catch (e) {
      console.error("Key polling error:", e)
    }
  }, 50)
}

async function processCapturedKey(key: string) {
  if (editingControlId.value) {
    const ctrl = [...controls.value, ...swipes.value].find(c => c.id === editingControlId.value)
    if (ctrl) {
      const dup = [...controls.value, ...swipes.value].find(c => c.id !== ctrl.id && c.key === key)
      if (!dup) {
        ctrl.key = key
        ctrl.label = getKeyLabel(key)
      }
      editingControlId.value = null
      autoSave()
    }
  } else if (editingDpadId.value && editingDpadDir.value) {
    const dpad = dpads.value.find(d => d.id === editingDpadId.value)
    if (dpad) {
      dpad.keys[editingDpadDir.value] = { key: key, label: getKeyLabel(key) }
    }
    editingDpadId.value = null
    editingDpadDir.value = null
    autoSave()
  }
}

function teardownKeyCapture() {
  if (keyPollTimer) {
    clearInterval(keyPollTimer)
    keyPollTimer = null
  }
  callApi("stop_key_listener").catch(() => {})
}

// ---- Mouse button capture (for left click creating controls, we need separate handling) ----
// This is handled via pointerdown detection on the overlay

// ---- Close overlay ----
async function closeKeyMapping() {
  await saveCurrentMapping()
  editingControlId.value = null
  editingDpadId.value = null
  editingDpadDir.value = null
  contextMenu.value.show = false
  isRecordingSwipe.value = false
  pendingSwipe.value = false
  swipePoints.value = []
  lastSwipePath.value = []
  teardownKeyCapture()
  showKeyMapping.value = false
  // Keep key mapping active for execution
  isKeyMappingActive.value = true
}

onMounted(async () => {
  fpsTimer = window.setInterval(() => {
    fps.value = framesThisSecond
    framesThisSecond = 0
  }, 1000)

  resizeObserver = new ResizeObserver((entries) => {
    const entry = entries[0]
    if (!entry) return
    viewportSize.value = {
      width: entry.contentRect.width,
      height: entry.contentRect.height,
    }
  })
  if (viewport.value) resizeObserver.observe(viewport.value)

  if (kmCanvasRef.value) {
    kmResizeObserver = new ResizeObserver(() => { updateKmCanvasSize() })
    kmResizeObserver.observe(kmCanvasRef.value)
  }

  window.addEventListener('blur', handleBlur)
  window.addEventListener('focus', handleFocus)

  // 添加键盘事件监听
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('keyup', handleKeyup)
  window.addEventListener('mousedown', handleMouseDown)
  window.addEventListener('mouseup', handleMouseUp)

  await nextTick()
  updateKmCanvasSize()

  await startConnection()
})

onBeforeUnmount(() => {
  if (fpsTimer) window.clearInterval(fpsTimer)
  resizeObserver?.disconnect()
  kmResizeObserver?.disconnect()
  kmResizeObserver = null
  window.removeEventListener('blur', handleBlur)
  window.removeEventListener('focus', handleFocus)
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('keyup', handleKeyup)
  window.removeEventListener('mousedown', handleMouseDown)
  window.removeEventListener('mouseup', handleMouseUp)
  teardownKeyCapture()

  stopConnection()
})

function handleMouseDown(_event: MouseEvent) {
  // 不再在前端处理按键映射，完全由后端处理
}

function handleMouseUp(_event: MouseEvent) {
  // 不再在前端处理按键映射，完全由后端处理
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isFullscreen.value) {
    toggleScrcpyFullscreen()
  }
}

function handleKeyup(_event: KeyboardEvent) {
  // 不再在前端处理按键映射，完全由后端处理
}

// 暴露函数给父组件调用

function handleBlur() {
  callApi("set_focus_state", false).catch(() => {})
}

function handleFocus() {
  callApi("set_focus_state", true).catch(() => {})
}
defineExpose({
  toggleScrcpyFullscreen
})
</script>






