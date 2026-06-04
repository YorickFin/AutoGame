<script setup lang="ts">
import { ref, computed, inject, onMounted, type Ref } from 'vue'

type Theme = 'light' | 'dark'

const currentTheme = inject<Ref<Theme>>('theme')

const emit = defineEmits<{
  (e: 'navigate', mode: 'usb' | 'wireless'): void
}>()

const connectionMode = ref<'usb' | 'wireless' | 'control_only' | null>(null)

const videoSource = ref<'display' | 'camera' | 'none'>('display')
const audioSource = ref<'output' | 'mic' | 'none'>('output')
const quality = ref<'1280' | '1920' | '2560' | '3840' | 'unlimited'>('unlimited')
const bitrate = ref(8)
const fpsLimit = ref(60)
const aspectRatio = ref<"16:9" | "monitor" | "reset">("reset")


const isOnlyControlMode = computed(() => {
  return videoSource.value === 'none' && audioSource.value === 'none'
})

const shouldDisableVideoSettings = computed(() => {
  return videoSource.value === 'none'
})

async function loadScreencastConfig() {
  try {
    const config = await (window as any).pywebview.api.get_config_file()
    const sc = config.screencast
    if (sc) {
      if (sc.videoSource && ['display', 'camera', 'none'].includes(sc.videoSource)) {
        videoSource.value = sc.videoSource
      }
      if (sc.audioSource && ['output', 'mic', 'none'].includes(sc.audioSource)) {
        audioSource.value = sc.audioSource
      }
      if (sc.quality && ['1280', '1920', '2560', '3840', 'unlimited'].includes(sc.quality)) {
        quality.value = sc.quality
      }
      if (sc.bitrate !== undefined && typeof sc.bitrate === 'number' && sc.bitrate >= 1 && sc.bitrate <= 100) {
        bitrate.value = sc.bitrate
      }
      if (sc.fpsLimit !== undefined && typeof sc.fpsLimit === 'number' && sc.fpsLimit >= 30 && sc.fpsLimit <= 360) {
        fpsLimit.value = sc.fpsLimit
      }
    }
  } catch (e) {
    console.error('Failed to load screencast config:', e)
  }
}

async function saveScreencastConfig() {
  if (!(window as any).pywebview?.api) {
    console.warn('pywebview API not available')
    return
  }
  try {
    const config = await (window as any).pywebview.api.get_config_file()
    config.screencast = {
      videoSource: videoSource.value,
      audioSource: audioSource.value,
      quality: quality.value,
      bitrate: bitrate.value,
      fpsLimit: fpsLimit.value,
      aspectRatio: aspectRatio.value,
    }
    await (window as any).pywebview.api.save_config_file(config)
  } catch (e) {
    if (e instanceof Error && e.message.includes('ObjectDisposedException')) {
      console.warn('Window is closing, skipping save')
    } else {
      console.error('Failed to save screencast config:', e)
    }
  }
}

async function pollForConfig() {
  const maxAttempts = 50
  let attempts = 0
  while (attempts < maxAttempts) {
    try {
      if ((window as any).pywebview && (window as any).pywebview.api) {
        await loadScreencastConfig()
        return
      }
    } catch (e) {
      // continue trying
    }
    attempts++
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  console.warn('Failed to load screencast config after multiple attempts')
}

onMounted(() => {
  pollForConfig()
})

function handleConnect(mode: 'usb' | 'wireless' | 'control_only') {
  if (mode === 'control_only' || !isOnlyControlMode.value) {
    if (mode === 'usb' || mode === 'wireless') {
      emit('navigate', mode)
    } else {
      connectionMode.value = mode
    }
  }
}

function handleDisconnect() {
  connectionMode.value = null
}

function selectVideoSource(source: 'display' | 'camera' | 'none') {
  videoSource.value = source
  saveScreencastConfig()
}

function selectAudioSource(source: 'output' | 'mic' | 'none') {
  audioSource.value = source
  saveScreencastConfig()
}

function selectQuality(q: '1280' | '1920' | '2560' | '3840' | 'unlimited') {
  if (!shouldDisableVideoSettings.value) {
    quality.value = q
    saveScreencastConfig()
  }
}

function selectBitrate(b: number) {
  if (!shouldDisableVideoSettings.value) {
    bitrate.value = b
    saveScreencastConfig()
  }
}

async function selectAspectRatio(ratio: "16:9" | "monitor" | "reset") {
  aspectRatio.value = ratio
  saveScreencastConfig()
  try {
    const result = await (window as any).pywebview.api.set_screencast_ratio(ratio)
    if (result && !result.ok) {
      console.error("应用屏幕比例失败:", result.error)
    }
  } catch (e) {
    console.error("调用屏幕比例API失败:", e)
  }
}

function selectFps(fps: number) {
  if (!shouldDisableVideoSettings.value) {
    fpsLimit.value = fps
    saveScreencastConfig()
  }
}
</script>

<style src="./Screencast.css" scoped></style>

<template>
  <div class="screencast-view" :data-theme="currentTheme">
    <h1 class="section-title">手机投屏</h1>

    <div class="connection-buttons">
      <button
        class="connect-btn usb-btn"
        :class="{ disabled: isOnlyControlMode, active: connectionMode === 'usb' }"
        @click="handleConnect('usb')"
        :disabled="isOnlyControlMode"
      >
        <svg viewBox="0 0 1024 1024" width="20" height="20">
          <g transform="scale(1) translate(0, 0)">
            <path d="M760 432V144c0-17.7-14.3-32-32-32H296c-17.7 0-32 14.3-32 32v288c-66.2 0-120 52.1-120 116v356c0 4.4 3.6 8 8 8h56c4.4 0 8-3.6 8-8V548c0-24.3 21.6-44 48.1-44H759.9c26.5 0 48.1 19.7 48.1 44v356c0 4.4 3.6 8 8 8h56c4.4 0 8-3.6 8-8V548c0-63.9-53.8-116-120-116z m-424 0V184h352v248H336z" fill="currentColor"/>
            <path d="M456 248h-48c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8zM616 248h-48c-4.4 0-8 3.6-8 8v48c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8z" fill="currentColor"/>
          </g>
        </svg>
        <span>USB连接</span>
      </button>

      <button
        class="connect-btn wireless-btn"
        :class="{ disabled: isOnlyControlMode, active: connectionMode === 'wireless' }"
        @click="handleConnect('wireless')"
        :disabled="isOnlyControlMode"
      >
        <svg viewBox="0 0 1024 1024" width="20" height="20">
          <g transform="scale(0.93) translate(50, 0)">
            <path d="M640 810.666667a128 128 0 1 0-256 0 128 128 0 0 0 256 0z m-170.666667 0a42.666667 42.666667 0 1 1 85.333334 0 42.666667 42.666667 0 0 1-85.333334 0zM1002.752 271.786667a42.666667 42.666667 0 1 1-65.408 54.869333A553.301333 553.301333 0 0 0 512 128C346.368 128 192.682667 200.96 87.893333 325.162667A42.666667 42.666667 0 0 1 22.613333 270.122667 638.592 638.592 0 0 1 512 42.666667c191.829333 0 369.92 84.949333 490.752 229.12z m-159.402667 139.136a42.666667 42.666667 0 0 1-65.365333 54.826666A346.496 346.496 0 0 0 511.573333 341.333333a346.453333 346.453333 0 0 0-265.642666 123.477334 42.666667 42.666667 0 0 1-65.194667-55.04A431.786667 431.786667 0 0 1 511.573333 256a431.786667 431.786667 0 0 1 331.776 154.922667z m-128 153.472a42.666667 42.666667 0 0 1-65.365333 54.826666A179.712 179.712 0 0 0 511.744 554.666667a179.712 179.712 0 0 0-137.813333 64.085333 42.666667 42.666667 0 0 1-65.194667-55.04A265.045333 265.045333 0 0 1 511.744 469.333333c79.573333 0 153.514667 35.285333 203.605333 95.061334z" fill="currentColor"/>
          </g>
        </svg>
        <span>无线连接</span>
      </button>

      <button
        class="connect-btn control-btn"
        :class="{ active: connectionMode === 'control_only' }"
        @click="handleConnect('control_only')"
      >
        <svg viewBox="0 0 1024 1024" width="20" height="20">
          <g transform="scale(1.2) translate(-85, -85)">
            <path d="M512 938.4C276.7 938.4 85.3 747 85.3 511.8S276.7 85.1 512 85.1s426.7 191.4 426.7 426.7S747.3 938.4 512 938.4z m0-775.7c-192.5 0-349.1 156.6-349.1 349.1S319.5 860.9 512 860.9s349.1-156.6 349.1-349.1S704.5 162.7 512 162.7z" fill="currentColor"/>
            <path d="M512 205.4l128 128H384l128-128z m0 612.8l128-128H384l128 128zM205.6 511.8l128-128v256l-128-128z m612.8 0l-128-128v256l128-128z" fill="currentColor"/>
          </g>
        </svg>
        <span>仅控制</span>
      </button>
      <button
        class="connect-btn disconnect-btn"

        @click="handleDisconnect"
      >
        <svg viewBox="0 0 1024 1024" width="20" height="20">
          <g transform="scale(1) translate(0, 0)">
            <path d="M816.952281 614.064456l-45.118858-45.118857L895.99028 447.98866a223.99433 223.99433 0 0 0-316.791981-316.791981l-124.156857 120.956938-45.118858-45.438849 122.556898-122.236906a287.99271 287.99271 0 0 1 407.029697 407.029697zM288.00567 1023.974081a287.99271 287.99271 0 0 1-203.514849-491.507559l122.556898-122.556898 45.118858 45.118858-122.556898 122.556898A223.99433 223.99433 0 0 0 448.00162 895.977321l122.556898-122.556898 45.118858 45.118858-122.556898 122.556898A285.752767 285.752767 0 0 1 288.00567 1023.974081zM137.257486 182.555379L182.50434 137.276525l255.897523 255.897523-45.246855 45.246854zM585.214147 630.544039l45.246854-45.246854 255.897523 255.897522-45.246855 45.246855z" fill="currentColor"/>
          </g>
        </svg>
        <span>断开连接</span>
      </button>
    </div>

    <div class="settings-grid">

      <!-- 视频来源 -->
      <div class="setting-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" stroke-linejoin="round"/>
            <path d="M8 21h8M12 17v4"/>
          </svg>
          <span class="card-title">视频来源</span>
        </div>
        <div class="option-group">
          <button
            class="option-btn"
            :class="{ active: videoSource === 'display' }"
            @click="selectVideoSource('display')"
          >
            手机屏幕
          </button>
          <button
            class="option-btn"
            :class="{ active: videoSource === 'camera' }"
            @click="selectVideoSource('camera')"
          >
            摄像头
          </button>
          <button
            class="option-btn"
            :class="{ active: videoSource === 'none' }"
            @click="selectVideoSource('none')"
          >
            不传输视频
          </button>
        </div>
      </div>

      <!-- 音频来源 -->
      <div class="setting-card">
        <div class="card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
          </svg>
          <span class="card-title">音频来源</span>
        </div>
        <div class="option-group">
          <button
            class="option-btn"
            :class="{ active: audioSource === 'output' }"
            @click="selectAudioSource('output')"
          >
            内部输入
          </button>
          <button
            class="option-btn"
            :class="{ active: audioSource === 'mic' }"
            @click="selectAudioSource('mic')"
          >
            麦克风
          </button>
          <button
            class="option-btn"
            :class="{ active: audioSource === 'none' }"
            @click="selectAudioSource('none')"
          >
            不传输音频
          </button>
        </div>
      </div>

      <!-- 适配比例 -->
      <div class="setting-card">
        <div class="card-header">
          <svg viewBox="0 0 1024 1024" width="22" height="22">
            <rect x="192" y="128" width="640" height="768" rx="48" stroke="currentColor" stroke-width="64" fill="none"/>
            <text x="512" y="660" font-size="400" font-weight="bold" text-anchor="middle" fill="currentColor">:</text>
          </svg>
          <span class="card-title">适配比例</span>
        </div>
        <div class="option-group">
          <button
            class="option-btn"
            :class="{ active: aspectRatio === '16:9' }"
            @click="selectAspectRatio('16:9')"
          >
            16 : 9
          </button>
          <button
            class="option-btn"
            :class="{ active: aspectRatio === 'monitor' }"
            @click="selectAspectRatio('monitor')"
          >
            显示器
          </button>
          <button
            class="option-btn"
            :class="{ active: aspectRatio === 'reset' }"
            @click="selectAspectRatio('reset')"
          >
            恢复默认
          </button>
        </div>
      </div>

      <!-- 分辨率 -->
      <div class="setting-card">
        <div class="card-header">
          <svg viewBox="0 0 1024 1024" width="22" height="22">
            <rect x="16" y="32" width="992" height="832" rx="64" stroke="currentColor" stroke-width="64" fill="none"/>
            <text x="512" y="590" font-size="480" font-weight="bold" text-anchor="middle" fill="currentColor">HD</text>
          </svg>
          <span class="card-title">分辨率</span>
        </div>
        <div class="option-group">
          <button
            class="option-btn"
            :class="{ active: quality === '1280', disabled: shouldDisableVideoSettings }"
            @click="selectQuality('1280')"
            :disabled="shouldDisableVideoSettings"
          >
            1280
          </button>
          <button
            class="option-btn"
            :class="{ active: quality === '1920', disabled: shouldDisableVideoSettings }"
            @click="selectQuality('1920')"
            :disabled="shouldDisableVideoSettings"
          >
            1920
          </button>
          <button
            class="option-btn"
            :class="{ active: quality === '2560', disabled: shouldDisableVideoSettings }"
            @click="selectQuality('2560')"
            :disabled="shouldDisableVideoSettings"
          >
            2560
          </button>
          <button
            class="option-btn"
            :class="{ active: quality === '3840', disabled: shouldDisableVideoSettings }"
            @click="selectQuality('3840')"
            :disabled="shouldDisableVideoSettings"
          >
            3840
          </button>
          <button
            class="option-btn"
            :class="{ active: quality === 'unlimited', disabled: shouldDisableVideoSettings }"
            @click="selectQuality('unlimited')"
            :disabled="shouldDisableVideoSettings"
          >
            不限制
          </button>
        </div>
      </div>

      <!-- 帧率限制 -->
      <div class="setting-card">
        <div class="card-header">
          <div class="header-left">
            <svg viewBox="0 0 1024 1024" width="22" height="22">
              <circle cx="512" cy="512" r="448" stroke="currentColor" stroke-width="64" fill="none"/>
              <text x="512" y="720" font-size="560" font-weight="bold" text-anchor="middle" fill="currentColor">F</text>
            </svg>
            <span class="card-title">帧率限制</span>
          </div>
          <div class="slider-value">{{ fpsLimit }} FPS</div>
          <div class="header-right"></div>
        </div>
        <div class="slider-group">
          <input
            type="range"
            min="30"
            max="360"
            :value="fpsLimit"
            @input="selectFps(Number(($event.target as HTMLInputElement).value))"
            :disabled="shouldDisableVideoSettings"
            class="bitrate-slider"
          />
        </div>
      </div>

      <!-- 比特率 -->
      <div class="setting-card">
        <div class="card-header">
          <div class="header-left">
            <svg viewBox="0 0 1024 1024" width="22" height="22">
              <rect x="32" y="400" width="64" height="224" rx="16" fill="currentColor"/>
              <rect x="200" y="288" width="64" height="448" rx="16" fill="currentColor"/>
              <rect x="368" y="176" width="64" height="672" rx="16" fill="currentColor"/>
              <rect x="536" y="288" width="64" height="448" rx="16" fill="currentColor"/>
              <rect x="704" y="400" width="64" height="224" rx="16" fill="currentColor"/>
            </svg>
            <span class="card-title">比特率</span>
          </div>
          <div class="slider-value">{{ bitrate }}M</div>
          <div class="header-right"></div>
        </div>
        <div class="slider-group">
          <input
            type="range"
            min="1"
            max="100"
            :value="bitrate"
            @input="selectBitrate(Number(($event.target as HTMLInputElement).value))"
            :disabled="shouldDisableVideoSettings"
            class="bitrate-slider"
          />
        </div>
      </div>
    </div>

    <div class="connection-status" v-if="connectionMode">
      <div class="status-indicator" :class="connectionMode"></div>
      <span>
        {{ connectionMode === 'usb' ? 'USB连接中' : connectionMode === 'wireless' ? '无线连接中' : '仅控制模式' }}
      </span>
    </div>
  </div>
</template>
