<template>
  <div
    class="key-mapping-overlay"
    @mousedown.left="onOverlayMouseDown"
    @mousemove="onOverlayMouseMove"
    @mouseup.left="onOverlayMouseUp"
    @click.right.prevent="onOverlayRightClick"
    @contextmenu.prevent
  >
    <div class="km-center-wrapper">
      <div class="key-mapping-canvas" ref="kmCanvasRef" :style="screenStyle" @mousedown.left.stop="onCanvasMouseDown($event)" @contextmenu.prevent.stop="onCanvasRightClick($event)">
        <!-- Single controls -->
        <div v-for="ctrl in controls" :key="ctrl.id"
             class="key-control"
             :class="{ listening: editingControlId === ctrl.id, 'is-mouse': ctrl.isMouse }"
             :style="ctrlStyle(ctrl)"
             @mousedown.left.stop="startDrag($event, ctrl)"
             @mouseup.left.stop="onControlMouseUp($event, ctrl)">
          <div class="control-circle">
            <span class="control-label" :style="ctrlLabelStyle(ctrl)">{{ ctrl.label || (editingControlId === ctrl.id ? '...' : '?') }}</span>
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
          <button class="control-close" @click.stop="removeControl(dpad.id)" :style="{ ...controlCloseStyle(dpad, true), position: 'absolute', zIndex: 10 }">&times;</button>
        </div>
        <!-- Swipe controls -->
        <div v-for="swp in swipes" :key="swp.id"
             class="key-control"
             :class="{ listening: editingControlId === swp.id }"
             :style="ctrlStyle(swp)"
             @mousedown.left.stop="startDrag($event, swp, 'swipe')"
             @mouseup.left.stop="onControlMouseUp($event, swp)">
          <div class="control-circle">
            <span class="control-label" :style="ctrlLabelStyle(swp)">{{ swp.label || '滑动' }}</span>
            <button class="control-close" @click.stop="removeControl(swp.id)" :style="controlCloseStyle(swp)">&times;</button>
          </div>
        </div>
        <svg v-if="isRecordingSwipe && swipePoints.length > 1" class="swipe-preview">
          <polyline :points="swipePoints.map((p: any) => (p.x * kmCanvasWidth) + ',' + (p.y * kmCanvasHeight)).join(' ')"></polyline>
        </svg>
        <svg v-if="lastSwipePath.length > 1" class="swipe-preview saved-swipe">
          <polyline :points="lastSwipePath.map((p: any) => (p.x * kmCanvasWidth) + ',' + (p.y * kmCanvasHeight)).join(' ')"></polyline>
        </svg>
        <svg v-for="swp in swipes" :key="'path-' + swp.id" v-show="swp.path && swp.path.length > 1" class="swipe-preview saved-swipe">
          <polyline :points="swp.path.map((p: any) => (p.x * kmCanvasWidth) + ',' + (p.y * kmCanvasHeight)).join(' ')"></polyline>
        </svg>
        <!-- Camera controls -->
        <div v-for="cam in cameras" :key="cam.id"
             class="key-control camera"
             :class="{ listening: editingControlId === cam.id }"
             :style="ctrlStyle(cam)"
             @mousedown.left.stop="startDrag($event, cam, 'camera')"
             @mouseup.left.stop="onControlMouseUp($event, cam)">
          <div class="control-circle camera-circle">
            <span class="control-label" :style="ctrlLabelStyle(cam)">{{ cam.label || '3D' }}</span>
            <button class="control-close" @click.stop="removeControl(cam.id)" :style="controlCloseStyle(cam)">&times;</button>
          </div>
        </div>
        <!-- Local Camera controls -->
        <div v-for="cam in cameras_local" :key="cam.id"
             class="key-control camera local"
             :class="{ listening: editingControlId === cam.id }"
             :style="ctrlStyle(cam)"
             @mousedown.left.stop="startDrag($event, cam, 'camera_local')"
             @mouseup.left.stop="onControlMouseUp($event, cam)">
          <div class="control-circle camera-circle local">
            <span class="control-label" :style="ctrlLabelStyle(cam)">{{ cam.label || 'LCam' }}</span>
            <button class="control-close" @click.stop="removeControl(cam.id)" :style="controlCloseStyle(cam)">&times;</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="contextMenu.show" class="context-menu"
         :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }">
      <div @click="createMouseLeft">鼠标左键</div>
      <div @click="createMouseRight">鼠标右键</div>
      <div @click="startSwipeRecording">滑动键位</div>
      <div @click="createDirectionKey">方向轮盘</div>
      <div @click="createCameraControl">全局3D控制</div>
      <div @click="createCameraLocalControl">局部3D控制</div>
    </div>
  </div>

  <Teleport to=".km-sidebar-target"><div v-if="!isFullscreen" class="key-mapping-sidebar">
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
    <div class="km-scale-section">
      <div class="km-scale-title">视角灵敏度</div>
      <div class="km-scale-row">
        <span class="km-scale-label active">X/Y</span>
        <input type="range" min="0.5" max="5.0" step="0.1" :value="cameraSensitivity" @input="cameraSensitivity = Number(($event.target as HTMLInputElement).value); autoSave()" />
        <span class="km-scale-value">{{ cameraSensitivity.toFixed(1) }}x</span>
      </div>
    </div>
    <div class="km-scale-section">
      <div class="km-scale-title">按钮大小</div>
      <div class="km-scale-row">
        <span class="km-scale-label" :class="{ active: isLandscape }">横屏</span>
        <input type="range" min="50" max="300" :value="scaleLandscape" @input="scaleLandscape = Number(($event.target as HTMLInputElement).value); autoSave()" />
        <span class="km-scale-value">{{ scaleLandscape }}%</span>
      </div>
      <div class="km-scale-row">
        <span class="km-scale-label" :class="{ active: !isLandscape }">竖屏</span>
        <input type="range" min="50" max="300" :value="scalePortrait" @input="scalePortrait = Number(($event.target as HTMLInputElement).value); autoSave()" />
        <span class="km-scale-value">{{ scalePortrait }}%</span>
      </div>
    </div>
    <div class="km-actions">
      <button class="km-btn close" @click="closeKeyMapping">关闭</button>
    </div>
  </div>
  </Teleport>


</template>
<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from "vue"
import "./ScreenCastKeyMapping.css"
import { callApi } from "../../composables/useScreencastApi"

const props = defineProps<{
  screenStyle: Record<string, string>
  currentTheme: string
  isFullscreen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
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

const keyMappingFiles = ref<string[]>([])
const currentFile = ref("")
const controls = ref<any[]>([])
const dpads = ref<any[]>([])
const swipes = ref<any[]>([])
const cameras = ref<any[]>([])
const cameras_local = ref<any[]>([])
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
const renamingFile = ref<string | null>(null)
const renameInput = ref("")
const renameInputRef = ref<HTMLInputElement | null>(null)
const kmCanvasRef = ref<HTMLElement | null>(null)

const scaleLandscape = ref(100)  // 横屏缩放百分比
const scalePortrait = ref(200)   // 竖屏缩放百分比（默认大60%）
const cameraSensitivity = ref(1.0)  // 视角灵敏度


let dragTarget: any = null
let dragOffsetX = 0
let dragOffsetY = 0
let dragStartPos = { x: 0, y: 0 }
let resizeTarget: any = null
let resizeStartSize = 0
let resizeStartMouse = { x: 0, y: 0 }
let autoSaveTimer = 0
let keyPollTimer: number | null = null

const isLandscape = computed(() => kmCanvasWidth.value > kmCanvasHeight.value)
const orientationScale = computed(() => (isLandscape.value ? scaleLandscape.value : scalePortrait.value) / 100)

let kmResizeObserver: ResizeObserver | null = null

function updateKmCanvasSize() {
  if (!kmCanvasRef.value) return
  const rect = kmCanvasRef.value.getBoundingClientRect()
  kmCanvasWidth.value = rect.width
  kmCanvasHeight.value = rect.height
}

function toNormalizedCoords(clientX: number, clientY: number) {
  if (!kmCanvasRef.value) return { x: 0, y: 0 }
  const rect = kmCanvasRef.value.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return { x: 0, y: 0 }
  return {
    x: (clientX - rect.left) / rect.width,
    y: (clientY - rect.top) / rect.height,
  }
}

function ctrlStyle(item: any, isDpad = false) {
  if (!kmCanvasRef.value) return {}
  const pw = kmCanvasWidth.value, ph = kmCanvasHeight.value
  const canvasSize = Math.max(pw, ph)
  if (pw <= 0 || ph <= 0) return {}
  if (isDpad) {
    const s = (item.size || 0.06) * canvasSize
    return { left: (item.x*pw)+"px", top: (item.y*ph)+"px", width: s+"px", height: s+"px" }
  }
  const r = canvasSize * (item.radius || 25) / 1000 * orientationScale.value
  const fontSize = r * 0.5
  return { left: (item.x*pw)+"px", top: (item.y*ph)+"px", width: (r*2)+"px", height: (r*2)+"px", fontSize: fontSize+"px" }
}

function ctrlLabelStyle(item: any) {
  if (!kmCanvasRef.value) return {}
  const pw = kmCanvasWidth.value, ph = kmCanvasHeight.value
  const canvasSize = Math.max(pw, ph)
  if (pw <= 0) return {}
  const r = canvasSize * (item.radius || 25) / 1000 * orientationScale.value
  const fontSize = r * 0.6
  return { fontSize: fontSize+"px" }
}

function controlCloseStyle(item: any, isDpad = false) {
  if (!kmCanvasRef.value) return {}
  const pw = kmCanvasWidth.value, ph = kmCanvasHeight.value
  const canvasSize = Math.max(pw, ph)
  if (pw <= 0) return {}
  const r = canvasSize * (item.radius || 25) / 1000 * (isDpad ? 1 : orientationScale.value)
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
  if (!kmCanvasRef.value) return {}
  const pw = kmCanvasWidth.value, ph = kmCanvasHeight.value
  const canvasSize = Math.max(pw, ph)
  if (pw <= 0) return {}
  const s = (dpad.size || 0.06) * canvasSize, r = s/2, o = r*0.6
  const keySize = r * 0.4
  const fontSize = keySize * 0.55
  const angles: Record<string, number> = {up:-90,down:90,left:180,right:0}
  const a = (angles[dir] ?? 0) * Math.PI/180
  return { left: (r+o*Math.cos(a)-keySize/2)+"px", top: (r+o*Math.sin(a)-keySize/2)+"px", width: keySize+"px", height: keySize+"px", lineHeight: keySize+"px", textAlign:"center" as const, fontSize: fontSize+"px", position:"absolute" as const, cursor:"pointer", background:"rgba(255,255,255,0.2)", borderRadius: (keySize*0.2)+"px", color:"#fff", userSelect:"none" as const }
}

function resizeHandleStyle(item: any, position: string) {
  if (!kmCanvasRef.value) return {}
  const pw = kmCanvasWidth.value, ph = kmCanvasHeight.value
  const canvasSize = Math.max(pw, ph)
  if (pw <= 0) return {}
  const s = (item.size || 0.06) * canvasSize
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
  if (!skipSave) await saveCurrentMapping()
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
      cameras.value = (data.camera || []).map((cam: any) => ({ ...cam }))
      cameras_local.value = (data.cameras_local || []).map((cam: any) => ({ ...cam }))
      scaleLandscape.value = data.scaleLandscape ?? 100
      scalePortrait.value = data.scalePortrait ?? 200
      cameraSensitivity.value = data.cameraSensitivity ?? 1.0
    } else {
      controls.value = []; dpads.value = []; swipes.value = []; cameras.value = []; cameras_local.value = []; scaleLandscape.value = 100; scalePortrait.value = 200
      cameraSensitivity.value = 1.0
    }
    await callApi("apply_key_mapping", name)
    await saveSelectedKeyMappingFile(name)
    nextTick(() => updateKmCanvasSize())
  } catch (e) {
    controls.value = []; dpads.value = []; swipes.value = []; cameras.value = []
    console.error("Failed to load key mapping:", e)
  }
}

async function saveCurrentMapping() {
  if (!currentFile.value) return
  const data = {
    version: 1,
    name: currentFile.value,
    scaleLandscape: scaleLandscape.value,
    scalePortrait: scalePortrait.value,
    cameraSensitivity: cameraSensitivity.value,
    controls: controls.value.map((c: any) => ({ id: c.id, type: "single", key: c.key, label: c.label, isMouse: !!c.isMouse, x: c.x, y: c.y, radius: c.radius })),
    dpad: dpads.value.map((d: any) => ({ id: d.id, type: "dpad", x: d.x, y: d.y, size: d.size, keys: d.keys })),
    swipes: swipes.value.map((s: any) => ({ id: s.id, type: "swipe", label: s.label, key: s.key || "", x: s.x, y: s.y, radius: s.radius, path: s.path })),
    camera: cameras.value.map((cam: any) => ({ id: cam.id, type: "camera", key: cam.key, label: cam.label, x: cam.x, y: cam.y, radius: cam.radius })),
    cameras_local: cameras_local.value.map((cam: any) => ({ id: cam.id, type: "camera_local", key: cam.key, label: cam.label, x: cam.x, y: cam.y, radius: cam.radius })),
  }
  try {
    await callApi("save_key_mapping_file", currentFile.value, data)
    await callApi("apply_key_mapping", currentFile.value)
  } catch (e) { console.error("Failed to save key mapping:", e) }
}

async function createNewKeyMapping() {
  try {
    const name = await callApi("create_key_mapping_file")
    if (name) { keyMappingFiles.value.push(name); await switchFile(name) }
  } catch (e) { console.error("Failed to create key mapping:", e) }
}

function startRename(name: string) {
  renamingFile.value = name; renameInput.value = name
  nextTick(() => renameInputRef.value?.focus())
}

async function doRename() {
  if (!renamingFile.value || !renameInput.value.trim()) { renamingFile.value = null; return }
  const oldName = renamingFile.value; const newName = renameInput.value.trim()
  renamingFile.value = null
  if (oldName === newName) return
  try {
    await callApi("rename_key_mapping_file", oldName, newName)
    const idx = keyMappingFiles.value.indexOf(oldName)
    if (idx >= 0) keyMappingFiles.value[idx] = newName
    if (currentFile.value === oldName) currentFile.value = newName
  } catch (e) { console.error("Failed to rename:", e) }
}

async function deleteFile(name: string) {
  try {
    await callApi("delete_key_mapping_file", name)
    keyMappingFiles.value = keyMappingFiles.value.filter(f => f !== name)
    if (currentFile.value === name) {
      currentFile.value = keyMappingFiles.value[0] || ""
      controls.value = []; dpads.value = []; swipes.value = []; cameras.value = []; cameras_local.value = []; lastSwipePath.value = []
      editingControlId.value = null; editingDpadId.value = null; editingDpadDir.value = null
      if (currentFile.value) await switchFile(currentFile.value, true)
    }
  } catch (e) { console.error("Failed to delete:", e) }
}

function onCanvasMouseDown(e: MouseEvent) {
  if (!kmCanvasRef.value) return
  contextMenu.value.show = false
  if (pendingSwipe.value) {
    pendingSwipe.value = false; isRecordingSwipe.value = true; swipePoints.value = []
    const pos = toNormalizedCoords(e.clientX, e.clientY)
    swipePoints.value = [{ x: pos.x, y: pos.y, delayMs: 0 }]; swipeStartTime.value = Date.now()
    return
  }
  if (isRecordingSwipe.value) return
  const pos = toNormalizedCoords(e.clientX, e.clientY)
  const ctrl = { id: controlId("ctrl"), key: "", label: "", x: pos.x, y: pos.y, radius: 12 }
  controls.value.push(ctrl); editingControlId.value = ctrl.id; setupKeyCapture()
}

function onCanvasRightClick(e: MouseEvent) {
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY }
}

function createMouseLeft() {
  contextMenu.value.show = false
  if (!kmCanvasRef.value) return
  const norm = toNormalizedCoords(contextMenu.value.x, contextMenu.value.y)
  const cam = {
    id: controlId("caml"),
    type: "camera_local",
    key: "MLeft",
    label: "MLeft",
    x: norm.x,
    y: norm.y,
    radius: 15
  }
  cameras_local.value.push(cam)
  autoSave()
}

function createMouseRight() {
  contextMenu.value.show = false
  if (!kmCanvasRef.value) return
  const norm = toNormalizedCoords(contextMenu.value.x, contextMenu.value.y)
  const cam = {
    id: controlId("caml"),
    type: "camera_local",
    key: "MRight",
    label: "MRight",
    x: norm.x,
    y: norm.y,
    radius: 15
  }
  cameras_local.value.push(cam)
  autoSave()
}

function onControlMouseUp(e: MouseEvent, ctrl: any) {
  const dx = e.clientX - dragStartPos.x
  const dy = e.clientY - dragStartPos.y
  const distance = Math.sqrt(dx * dx + dy * dy)
  dragTarget = null
  if (distance > 5) return
  if (ctrl && ctrl.isMouse) return
  editControl(ctrl)
}

function onOverlayRightClick(e: MouseEvent) {
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY }
}

function createDirectionKey() {
  contextMenu.value.show = false
  if (!kmCanvasRef.value) return
  const norm = toNormalizedCoords(contextMenu.value.x, contextMenu.value.y)
  const sizeNorm = 0.06
  dpads.value.push({
    id: controlId("dpad"), x: norm.x, y: norm.y, size: sizeNorm,
    keys: { up: { key: "W", label: "W" }, down: { key: "S", label: "S" }, left: { key: "A", label: "A" }, right: { key: "D", label: "D" } }
  })
  autoSave()
}

function startSwipeRecording() {
  contextMenu.value.show = false; pendingSwipe.value = true; updateKmCanvasSize()
}

function createCameraControl() {
  contextMenu.value.show = false
  if (!kmCanvasRef.value) return
  const norm = toNormalizedCoords(contextMenu.value.x, contextMenu.value.y)
  const cam = {
    id: controlId("cam"),
    type: "camera",
    key: "",
    label: "",
    x: norm.x,
    y: norm.y,
    radius: 15
  }
  cameras.value.push(cam)
  editingControlId.value = cam.id
  setupKeyCapture()
  autoSave()
}

function createCameraLocalControl() {
  contextMenu.value.show = false
  if (!kmCanvasRef.value) return
  const norm = toNormalizedCoords(contextMenu.value.x, contextMenu.value.y)
  const cam = {
    id: controlId("caml"),
    type: "camera_local",
    key: "",
    label: "",
    x: norm.x,
    y: norm.y,
    radius: 15
  }
  cameras_local.value.push(cam)
  editingControlId.value = cam.id
  setupKeyCapture()
  autoSave()
}

function onOverlayMouseDown() {}

function onOverlayMouseMove(e: MouseEvent) {
  if (isRecordingSwipe.value && swipeStartTime.value > 0 && kmCanvasRef.value) {
    const pos = toNormalizedCoords(e.clientX, e.clientY)
    const delay = Date.now() - swipeStartTime.value
    const last = swipePoints.value[swipePoints.value.length - 1]
    if (!last || Math.hypot(pos.x - last.x, pos.y - last.y) > 5 || delay - (last.delayMs || 0) > 30) {
      swipePoints.value.push({ x: pos.x, y: pos.y, delayMs: delay })
    }
  }
  if (dragTarget) {
    if (!kmCanvasRef.value) return
    const norm = toNormalizedCoords(e.clientX, e.clientY)
    const dx = (norm.x - dragOffsetX) - dragTarget.x
    const dy = (norm.y - dragOffsetY) - dragTarget.y
    dragTarget.x = Math.max(0, Math.min(1, norm.x - dragOffsetX))
    dragTarget.y = Math.max(0, Math.min(1, norm.y - dragOffsetY))
    if (dragTarget.path && Array.isArray(dragTarget.path)) {
      dragTarget.path.forEach((p: any) => { p.x += dx; p.y += dy })
    }
  }
}

function onOverlayMouseUp(e: MouseEvent) {
  if (isRecordingSwipe.value && swipePoints.value.length > 0 && kmCanvasRef.value) {
    isRecordingSwipe.value = false
    const pos = toNormalizedCoords(e.clientX, e.clientY)
    const lastDelay = Date.now() - swipeStartTime.value
    const lastPt = swipePoints.value[swipePoints.value.length - 1]
    if (!lastPt || lastPt.x !== pos.x || lastPt.y !== pos.y) {
      swipePoints.value.push({ x: pos.x, y: pos.y, delayMs: lastDelay })
    }
    lastSwipePath.value = swipePoints.value.map((p: any) => ({ ...p }))
    const swp = { id: controlId("swp"), label: "", key: "", x: pos.x, y: pos.y, radius: 12, path: lastSwipePath.value }
    swipes.value.push(swp); editingControlId.value = swp.id; setupKeyCapture()
    swipePoints.value = []; swipeStartTime.value = 0
  }
  if (dragTarget) { dragTarget = null; autoSave() }
  resizeTarget = null
}

function startDrag(e: MouseEvent, ctrl: any, _type = "single") {
  dragStartPos = { x: e.clientX, y: e.clientY }
  if (!kmCanvasRef.value || editingControlId.value) return
  const norm = toNormalizedCoords(e.clientX, e.clientY)
  dragTarget = ctrl; dragOffsetX = norm.x - ctrl.x; dragOffsetY = norm.y - ctrl.y
}

function startDpadResize(e: MouseEvent, dpad: any) {
  resizeTarget = dpad; resizeStartSize = dpad.size; resizeStartMouse = { x: e.clientX, y: e.clientY }
  document.addEventListener('mousemove', onResizeMouseMove)
  document.addEventListener('mouseup', onResizeMouseUp)
}

function onResizeMouseMove(e: MouseEvent) {
  if (!resizeTarget || !kmCanvasRef.value) return
  const rect = kmCanvasRef.value.getBoundingClientRect()
  const dx = (e.clientX - resizeStartMouse.x) / rect.width
  const dy = (e.clientY - resizeStartMouse.y) / rect.height
  const delta = Math.max(Math.abs(dx), Math.abs(dy)) * (dx + dy >= 0 ? 1 : -1)
  const minSize = 15 / Math.max(rect.width, rect.height)
  resizeTarget.size = Math.max(minSize, Math.min(0.5, resizeStartSize + delta))
}

function onResizeMouseUp() {
  resizeTarget = null
  document.removeEventListener('mousemove', onResizeMouseMove)
  document.removeEventListener('mouseup', onResizeMouseUp)
  autoSave()
}

function editControl(ctrl: any) {
  if (editingControlId.value === ctrl.id) {
    editingControlId.value = null
    teardownKeyCapture()
    if (!ctrl.key) {
      ctrl.label = '?'
    }
    return
  }
  editingControlId.value = ctrl.id
  editingDpadId.value = null
  editingDpadDir.value = null
  setupKeyCapture()
}

function editDpadKey(dpad: any, dir: string) {
  if (editingDpadId.value === dpad.id && editingDpadDir.value === dir) {
    editingDpadId.value = null
    editingDpadDir.value = null
    teardownKeyCapture()
    return
  }
  editingDpadId.value = dpad.id
  editingDpadDir.value = dir
  editingControlId.value = null
  setupKeyCapture()
}

function removeControl(id: string) {
  editingControlId.value = null
  editingDpadId.value = null
  editingDpadDir.value = null
  teardownKeyCapture()
  controls.value = controls.value.filter(c => c.id !== id)
  dpads.value = dpads.value.filter(d => d.id !== id)
  const removedSwipe = swipes.value.find(s => s.id === id)
  swipes.value = swipes.value.filter(s => s.id !== id)
  cameras.value = cameras.value.filter(cam => cam.id !== id)
  cameras_local.value = cameras_local.value.filter(cam => cam.id !== id)
  if (removedSwipe && lastSwipePath.value.length > 0) {
    if (JSON.stringify(lastSwipePath.value) === JSON.stringify(removedSwipe.path)) {
      lastSwipePath.value = []
    }
  }
  autoSave()
}

function autoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = window.setTimeout(() => saveCurrentMapping(), 500)
}

async function setupKeyCapture() {
  await callApi("start_key_listener")
  if (keyPollTimer) clearInterval(keyPollTimer)
  keyPollTimer = window.setInterval(async () => {
    try {
      const result = await callApi("get_pressed_key")
      if (result.key) {
        await processCapturedKey(result.key)
        await callApi("stop_key_listener")
        if (keyPollTimer) { clearInterval(keyPollTimer); keyPollTimer = null }
      }
    } catch (e) { console.error("Key polling error:", e) }
  }, 50)
}

async function processCapturedKey(key: string) {
  if (key === "MLeft" || key === "MRight") {
    return
  }
  if (editingControlId.value) {
    const ctrl = [...controls.value, ...swipes.value, ...cameras.value, ...cameras_local.value].find(c => c.id === editingControlId.value)
    if (ctrl) {
      if (![...controls.value, ...swipes.value, ...cameras.value, ...cameras_local.value].find(c => c.id !== ctrl.id && c.key === key)) {
        ctrl.key = key; ctrl.label = getKeyLabel(key)
      }
      editingControlId.value = null; autoSave()
    }
  } else if (editingDpadId.value && editingDpadDir.value) {
    const dpad = dpads.value.find(d => d.id === editingDpadId.value)
    if (dpad) dpad.keys[editingDpadDir.value] = { key, label: getKeyLabel(key) }
    editingDpadId.value = null; editingDpadDir.value = null; autoSave()
  }
}

function teardownKeyCapture() {
  if (keyPollTimer) { clearInterval(keyPollTimer); keyPollTimer = null }
  callApi("stop_key_listener").catch(() => {})
}

async function closeKeyMapping() {
  await saveCurrentMapping()
  editingControlId.value = null; editingDpadId.value = null; editingDpadDir.value = null
  contextMenu.value.show = false; isRecordingSwipe.value = false; pendingSwipe.value = false
  swipePoints.value = []; lastSwipePath.value = []
  teardownKeyCapture()
  emit('close')
}

onMounted(async () => {
  if (kmCanvasRef.value) {
    kmResizeObserver = new ResizeObserver(() => updateKmCanvasSize())
    kmResizeObserver.observe(kmCanvasRef.value)
  }
  await nextTick(); updateKmCanvasSize()
  await loadKeyMappingOnConnect()
})

onBeforeUnmount(() => {
  kmResizeObserver?.disconnect(); kmResizeObserver = null
  teardownKeyCapture()
})
</script>
