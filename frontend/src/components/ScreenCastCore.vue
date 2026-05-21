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
        <ScreenCastKeyMapping
          v-if="showKeyMapping"
          :screen-style="screenStyle"
          :session-width="session.width"
          :session-height="session.height"
          :current-theme="currentTheme"
          :is-fullscreen="isFullscreen"
          @close="closeKeyMapping"
        />
      </div>
    </div>
    <div class="km-sidebar-target"></div>
    <ScreenCastToolbar
      v-if="!isFullscreen"
      :is-fullscreen="isFullscreen"
      :show-fps="showFps"
      :hovered-buttons="hoveredButtons"
      @toggle-key-mapping="toggleKeyMapping"
      @scrcpy-vol-up="scrcpyVolumeUp"
      @scrcpy-vol-down="scrcpyVolumeDown"
      @toggle-fullscreen="toggleScrcpyFullscreen"
      @toggle-fps="handleToolbarToggleFps"
      @scrcpy-back="scrcpyBack"
      @scrcpy-switch-app="scrcpySwitchApp"
      @scrcpy-home="scrcpyHome"
      @show-tooltip="showTooltip"
      @hide-tooltip="hideTooltip"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted, onBeforeUnmount, nextTick, type Ref } from "vue"
import { callApi } from "../composables/useScreencastApi"
import ScreenCastToolbar from "./ScreenCastToolbar.vue"
import ScreenCastKeyMapping from "./ScreenCastKeyMapping.vue"
import "./ScreenCastCore.css"

type Theme = "light" | "dark"

const currentTheme = inject<Ref<Theme>>("theme", ref("dark"))

const props = defineProps<{
  connectionMode: "usb" | "wireless"
}>()

const emit = defineEmits<{
  (e: "back"): void
  (e: "fullscreen-change", isFull: boolean): void
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
const viewport = ref<HTMLElement | null>(null)
const viewportSize = ref({ width: 0, height: 0 })
const session = ref({ width: 0, height: 0 })
const fps = ref(0)
const showFps = ref(true)
const statusText = ref("Connecting...")
const status = ref<{ running: boolean; deviceName?: string | null; error?: string | null }>({
  running: false,
})
const hoveredButtons = ref<Record<string, string>>({})
const isFullscreen = ref(false)
const showKeyMapping = ref(false)
const isKeyMappingActive = ref(false)
let ws: WebSocket | null = null
let pendingMeta: { kind: string; pts?: number; keyFrame?: boolean; config?: boolean } | null = null
let wsReconnectAttempts = 0
const MAX_WS_RECONNECT = 3

const screenStyle = computed((): Record<string, string> => {
  if (!session.value.width || !session.value.height) return {} as Record<string, string>
  const padding = 0
  const aw = Math.max(1, viewportSize.value.width - padding)
  const ah = Math.max(1, viewportSize.value.height - padding)
  const scale = Math.min(aw / session.value.width, ah / session.value.height)
  return {
    width: `${Math.floor(session.value.width * scale)}px`,
    height: `${Math.floor(session.value.height * scale)}px`,
  }
})

function showTooltip(key: string, text: string) {
  hoveredButtons.value[key] = text
}

function hideTooltip(key: string) {
  delete hoveredButtons.value[key]
}

function scrcpyVolumeUp() {
  callApi("scrcpy_volume_up").catch(() => {})
}

function scrcpyVolumeDown() {
  callApi("scrcpy_volume_down").catch(() => {})
}

function toggleScrcpyFullscreen() {
  isFullscreen.value = !isFullscreen.value
  emit('fullscreen-change', isFullscreen.value)
  if ((window as any).pywebview && (window as any).pywebview.api) {
    (window as any).pywebview.api.toggle_maximize()
  }
}

function handleToolbarToggleFps() {
  toggleShowFps()
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
  stopConnection()
  emit("back")
}

let videoDecoder: VideoDecoder | null = null
let audioContext: AudioContext | null = null
let audioScheduleEnd: number = 0
const MAX_AUDIO_SCHEDULE_HEAD = 0.15
const AUDIO_SCHEDULE_OFFSET = 0.005
let videoConfigured = false
let fpsTimer = 0
let framesThisSecond = 0
let resizeObserver: ResizeObserver | null = null

async function initKeyMappingBackground() {
  try {
    const config = await callApi("get_config_file")
    const savedFileName = config.keyMappingFile
    if (savedFileName) {
      await callApi("apply_key_mapping", savedFileName)
      return
    }
    const files = await callApi("get_key_mapping_files")
    if (files.length > 0) {
      await callApi("apply_key_mapping", files[0])
      config.keyMappingFile = files[0]
      await callApi("save_config_file", config)
    } else {
      const newFile = await callApi("create_key_mapping_file")
      if (newFile) {
        await callApi("apply_key_mapping", newFile)
        config.keyMappingFile = newFile
        await callApi("save_config_file", config)
      }
    }
  } catch (e) {
    console.error("Failed to init key mapping:", e)
  }
}

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
      const serial = await callApi("scrcpy_discover_usb_serial")
      resolvedSerial = serial || undefined
    }
    status.value = await callApi("scrcpy_start", resolvedSerial || null, scConfig)
    if (status.value.running) {
      statusText.value = `Connected to ${status.value.deviceName || "device"}`
      const wsPort = await callApi("scrcpy_get_ws_port")
      if (wsPort > 0) {
        startWebSocket(wsPort)
      }
      await initKeyMappingBackground()
    } else {
      statusText.value = status.value.error || "Connection failed"
    }
  } catch (e) {
    statusText.value = e instanceof Error ? e.message : String(e)
  }
}

async function stopConnection() {
  closeWebSocket()
  closeDecoders()
  try {
    await callApi("scrcpy_stop")
  } catch {
    // ignore
  }
  status.value = { running: false }
}

function startWebSocket(port: number) {
  closeWebSocket()
  wsReconnectAttempts = 0
  ws = new WebSocket(`ws://localhost:${port}`)
  ws.binaryType = "arraybuffer"

  ws.onopen = () => {
    wsReconnectAttempts = 0
  }

  ws.onmessage = (event: MessageEvent) => {
    if (typeof event.data === "string") {
      const meta = JSON.parse(event.data)
      if (meta.kind === "session") {
        session.value = { width: meta.width || 0, height: meta.height || 0 }
        resizeCanvas()
        pendingMeta = null
      } else {
        pendingMeta = meta
      }
    } else {
      if (!pendingMeta) return
      const { kind, pts, keyFrame, config } = pendingMeta
      const data = new Uint8Array(event.data as ArrayBuffer)
      if (kind === "video") {
        framesThisSecond++
        decodeVideoBytes(data, { pts, keyFrame, config })
      } else if (kind === "audio") {
        playAudioBytes(data)
      }
      pendingMeta = null
    }
  }

  ws.onclose = () => {
    ws = null
    if (wsReconnectAttempts < MAX_WS_RECONNECT) {
      wsReconnectAttempts++
      setTimeout(() => {
        if (status.value.running) startWebSocket(port)
      }, 1000)
    } else {
      statusText.value = "WebSocket disconnected"
    }
  }

  ws.onerror = () => {
    ws?.close()
  }
}

function closeWebSocket() {
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  pendingMeta = null
  wsReconnectAttempts = 0
}



function decodeVideoBytes(data: Uint8Array, meta: { pts?: number | null; keyFrame?: boolean; config?: boolean }) {
  if (!("VideoDecoder" in window)) {
    return
  }
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
        } else {
        }
        frame.close()
      },
      error(e) {
        console.error("VideoDecoder error:", e.message)
      },
    })
  }
  // Only accept key frames until decoder is configured
  if (!videoConfigured) {
    if (!meta.keyFrame) {
      return
    }
    videoDecoder.configure({
      codec: "avc1.42E01E",
      optimizeForLatency: true,
      avc: { format: "annexb" },
    } as VideoDecoderConfig)
    videoConfigured = true
  }
  // Skip config-only events (SPS/PPS without a video frame)
  if (meta.config && !meta.keyFrame) return
  // Accept all frames once configured
  const chunk = new EncodedVideoChunk({
    type: meta.keyFrame ? "key" : "delta",
    timestamp: meta.pts || performance.now() * 1000,
    data,
  })
  try {
    videoDecoder.decode(chunk)
  } catch (e) {
    console.error("Decode error:", e)
  }
}

function playAudioBytes(data: Uint8Array) {
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
  const now = audioContext.currentTime
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

function resizeCanvas() {
  const cvs = canvas.value
  if (!cvs || !session.value.width || !session.value.height) return
  cvs.width = session.value.width
  cvs.height = session.value.height
}

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

function toggleKeyMapping() {
  showKeyMapping.value = !showKeyMapping.value
}

function closeKeyMapping() {
  showKeyMapping.value = false
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
  window.addEventListener('blur', handleBlur)
  window.addEventListener('focus', handleFocus)
  window.addEventListener('keydown', handleKeydown)
  window.addEventListener('keyup', handleKeyup)
  await nextTick()
  await startConnection()
})

onBeforeUnmount(() => {
  if (fpsTimer) window.clearInterval(fpsTimer)
  resizeObserver?.disconnect()
  window.removeEventListener('blur', handleBlur)
  window.removeEventListener('focus', handleFocus)
  window.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('keyup', handleKeyup)
  stopConnection()
})

function handleBlur() {
  callApi("set_focus_state", false).catch(() => {})
}

function handleFocus() {
  callApi("set_focus_state", true).catch(() => {})
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isFullscreen.value) {
    toggleScrcpyFullscreen()
  }
}

function handleKeyup(_event: KeyboardEvent) {
}
defineExpose({
  toggleScrcpyFullscreen
})
</script>
