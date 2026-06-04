"""Key mapping executor that sends touch events via scrcpy control stream."""

from __future__ import annotations

import math
import re
import threading
import time
import logging
from autoxkit.mousekey.mouse import Mouse

from ..services import services


logger = logging.getLogger(__name__)


class KeyMappingExecutor:
    def __init__(self):
        self._active_mapping = None
        self._enabled = False
        self._enabled_before_focus = False
        self._down_state_keys: dict[str, tuple[int, float, float]] = {}  # single-control key -> (pointer_id, x, y)
        self._dpad_states: dict[int, dict] = {}  # dpad index -> {pressed: set[str], pid: int|None, ex: float, ey: float}
        self._camera_active = False  # 3D视角模式是否激活
        self._camera_config = None   # 当前相机控件配置
        self._camera_center = (0.5, 0.5)
        self._camera_touch_x = 0         # 当前触摸位置 X（像素）
        self._camera_touch_y = 0         # 当前触摸位置 Y（像素）
        self._camera_screen_width = 0    # 设备屏幕宽度
        self._camera_screen_height = 0   # 设备屏幕高度
        self._camera_sensitivity = 1.0   # 视角灵敏度（从 mapping data 读取）
        self._camera_mouse = None            # Mouse 实例（延时初始化）
        self._camera_monitor_center = (0, 0) # 显示器中心
        self._camera_boundary_radius_sq = 10000  # 100²
        self._camera_last_mouse = (0, 0)     # 上次轮询的鼠标位置
        self._camera_poll_thread = None      # 轮询线程
        self._camera_poll_stop = threading.Event()  # 停止信号
        self._camera_lock = threading.Lock() # 保护共享状态
        self._keyboard_shown: bool | None = None
        self._keyboard_just_hidden = False
        self._last_notify_state: tuple[bool, bool] | None = None  # 上一次通知的状态，用于状态互斥
        self._kb_poll_stop = threading.Event()
        self._kb_poll_thread: threading.Thread | None = None
        self._kb_poll_started = False

    _DIR_VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    _OPPOSITE_DIRS = {"up": "down", "down": "up", "left": "right", "right": "left"}

    @property
    def scrcpy(self):
        return services.scrcpy

    @property
    def api(self):
        try:
            return services.api
        except AttributeError:
            return None

    @property
    def window(self):
        try:
            return services.window
        except AttributeError:
            return None

    def apply(self, mapping_data):
        self._active_mapping = mapping_data
        self._enabled = True
        self._camera_sensitivity = mapping_data.get('cameraSensitivity', 1.0)
        self._start_keyboard_poll()

    def remove(self):
        self.reset()
        self._active_mapping = None
        self._enabled = False

    @property
    def enabled(self):
        return self._enabled and self._active_mapping is not None

    def get_mapped_keys(self):
        """Return set of all configured keys."""
        keys = set()
        if not self._active_mapping:
            return keys
        for ctrl in self._active_mapping.get("controls", []):
            k = ctrl.get("key")
            if k:
                keys.add(k)
        for swp in self._active_mapping.get("swipes", []):
            k = swp.get("key")
            if k:
                keys.add(k)
        for dpad in self._active_mapping.get("dpad", []):
            for _, info in dpad.get("keys", {}).items():
                k = info.get("key")
                if k:
                    keys.add(k)
        for cam in self._active_mapping.get("camera", []):
            k = cam.get("key")
            if k:
                keys.add(k)
        return keys

    @staticmethod
    def _resolve_edge(pressed_keys, key_to_dir, cx, cy, radius, sw=None, sh=None):
        """Resolve the edge position from a set of pressed dpad keys.

        When *sw* and *sh* (screen pixel dimensions) are provided the direction
        is normalised in pixel-weighted space, so diagonal directions land at the
        correct angle regardless of the screen aspect ratio.
        """
        if not pressed_keys:
            return None
        dx = sum(KeyMappingExecutor._DIR_VECTORS[key_to_dir[k]][0] for k in pressed_keys if k in key_to_dir)
        dy = sum(KeyMappingExecutor._DIR_VECTORS[key_to_dir[k]][1] for k in pressed_keys if k in key_to_dir)

        if sw is not None and sh is not None and sw > 0 and sh > 0 and dx != 0 and dy != 0:
            # Aspect-ratio-aware normalisation: weight components by inverse screen
            # dimensions so the touch position has the correct angle in pixel space.
            dx_w = dx / sw
            dy_w = dy / sh
            length_w = math.sqrt(dx_w * dx_w + dy_w * dy_w)
            if length_w == 0:
                return None
            return (cx + dx_w / length_w * radius, cy + dy_w / length_w * radius)

        # Fallback: pure unit-vector normalisation (cardinal-only or missing dims)
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return None
        return (cx + dx / length * radius, cy + dy / length * radius)

    def on_key_down(self, key_name):
        """Handle key press - send touch events at control positions."""
        if not self._enabled or not self._active_mapping:
            return False

        if key_name in self._down_state_keys:
            return False

        # Check camera controls (toggle mode)
        for cam in self._active_mapping.get("camera", []):
            if cam.get("key") == key_name:
                self._toggle_camera_mode(cam)
                return True

        # Check single controls
        for ctrl in self._active_mapping.get("controls", []):
            if ctrl.get("key") == key_name:
                x = ctrl.get("x", 0.5)
                y = ctrl.get("y", 0.5)
                resp = self.scrcpy.send_normalized_touch(0, x, y)
                if resp.get("ok"):
                    pid = resp.get("pointer_id")
                    if pid is not None:
                        self._down_state_keys[key_name] = (pid, x, y)
                return True

        # Check swipes
        for swp in self._active_mapping.get("swipes", []):
            if swp.get("key") == key_name:
                path = swp.get("path", [])
                if path:
                    self.scrcpy.key_mapping_swipe(path)
                return True

        # Check dpad
        for dpad_idx, dpad in enumerate(self._active_mapping.get("dpad", [])):
            keys_config = dpad.get("keys", {})

            # Build key -> dir_name and dir_name -> key lookups
            key_to_dir = {}
            dir_to_key = {}
            for dir_name, info in keys_config.items():
                k = info.get("key")
                if k:
                    key_to_dir[k] = dir_name
                    dir_to_key[dir_name] = k

            if key_name not in key_to_dir:
                continue

            cx = dpad.get("x", 0.5)
            cy = dpad.get("y", 0.5)
            radius = dpad.get("size", 0.06)  # full radius to circle edge

            # Get screen dimensions for aspect-ratio-aware diagonal normalisation
            _sw, _sh = self.scrcpy._last_session if self.scrcpy._last_session else (None, None)

            # Initialize state for this dpad
            if dpad_idx not in self._dpad_states:
                self._dpad_states[dpad_idx] = {"pressed": set(), "pid": None, "ex": 0.0, "ey": 0.0}

            state = self._dpad_states[dpad_idx]

            # Ignore duplicate press
            if key_name in state["pressed"]:
                return True

            old_pressed = set(state["pressed"])

            # Handle opposite-direction replacement
            new_dir_name = key_to_dir[key_name]
            opposite_dir = self._OPPOSITE_DIRS.get(new_dir_name)
            to_remove = None
            if opposite_dir and opposite_dir in dir_to_key:
                opp_key = dir_to_key[opposite_dir]
                if opp_key in old_pressed:
                    to_remove = opp_key

            # Compute old edge position
            old_edge = self._resolve_edge(old_pressed, key_to_dir, cx, cy, radius, _sw, _sh)

            # Build new pressed set
            new_pressed = set(old_pressed)
            if to_remove:
                new_pressed.discard(to_remove)
            new_pressed.add(key_name)
            state["pressed"] = new_pressed

            new_edge = self._resolve_edge(new_pressed, key_to_dir, cx, cy, radius, _sw, _sh)

            if new_edge is None:
                # All directions canceled out — release
                if state["pid"] is not None:
                    self.scrcpy.send_normalized_touch(1, state["ex"], state["ey"], pointer_id=state["pid"])
                    state["pid"] = None
                return True

            if old_edge is None:
                # No previous touch — start fresh from center
                resp = self.scrcpy.send_normalized_touch(0, cx, cy)
                if resp.get("ok"):
                    pid = resp.get("pointer_id")
                    if pid is not None:
                        self.scrcpy.send_normalized_touch(2, new_edge[0], new_edge[1], pointer_id=pid)
                        state["pid"] = pid
                        state["ex"], state["ey"] = new_edge
                return True

            # Both old and new exist → decide restart or move
            ox, oy = old_edge
            nx, ny = new_edge
            old_len = math.sqrt((ox - cx) ** 2 + (oy - cy) ** 2)
            new_len = math.sqrt((nx - cx) ** 2 + (ny - cy) ** 2)
            if old_len > 0 and new_len > 0:
                dot = ((ox - cx) / old_len) * ((nx - cx) / new_len) + ((oy - cy) / old_len) * ((ny - cy) / new_len)
            else:
                dot = 1.0

            if dot < 0:
                # Opposite direction → restart touch at center
                self.scrcpy.send_normalized_touch(1, state["ex"], state["ey"], pointer_id=state["pid"])
                resp = self.scrcpy.send_normalized_touch(0, cx, cy)
                if resp.get("ok"):
                    pid = resp.get("pointer_id")
                    if pid is not None:
                        self.scrcpy.send_normalized_touch(2, nx, ny, pointer_id=pid)
                        state["pid"] = pid
                        state["ex"], state["ey"] = nx, ny
            else:
                # Same general direction → just move touch
                self.scrcpy.send_normalized_touch(2, nx, ny, pointer_id=state["pid"])
                state["ex"], state["ey"] = nx, ny

            return True

        key_code = self.scrcpy.ANDROID_KEYCODE_MAP.get(key_name, None)
        if self._keyboard_shown and key_code == 67:
            self.scrcpy.send_keycode(key_code, 0)
            return True
        elif not self._keyboard_shown and key_code:
            self.scrcpy.send_keycode(key_code, 0)
            return True

        return False

    def on_key_up(self, key_name):
        """Handle key release - send touch up at control position."""
        if not self._enabled or not self._active_mapping:
            return False

        # Check single controls
        item = self._down_state_keys.pop(key_name, None)
        if item is not None:
            pid, px, py = item
            self.scrcpy.send_normalized_touch(1, px, py, pointer_id=pid)
            return True

        # Check dpad
        for dpad_idx, dpad in enumerate(self._active_mapping.get("dpad", [])):
            keys_config = dpad.get("keys", {})

            key_to_dir = {}
            for dir_name, info in keys_config.items():
                k = info.get("key")
                if k:
                    key_to_dir[k] = dir_name

            if key_name not in key_to_dir:
                continue

            if dpad_idx not in self._dpad_states:
                return True

            state = self._dpad_states[dpad_idx]
            state["pressed"].discard(key_name)

            if not state["pressed"]:
                # No more keys — release touch
                if state["pid"] is not None:
                    self.scrcpy.send_normalized_touch(1, state["ex"], state["ey"], pointer_id=state["pid"])
                    state["pid"] = None
            else:
                # Update touch to new edge position
                cx = dpad.get("x", 0.5)
                cy = dpad.get("y", 0.5)
                radius = dpad.get("size", 0.06)
                new_edge = self._resolve_edge(state["pressed"], key_to_dir, cx, cy, radius, self.scrcpy._last_session[0] if self.scrcpy._last_session else None, self.scrcpy._last_session[1] if self.scrcpy._last_session else None)
                if new_edge is not None and state["pid"] is not None:
                    self.scrcpy.send_normalized_touch(2, new_edge[0], new_edge[1], pointer_id=state["pid"])
                    state["ex"], state["ey"] = new_edge

            return True

        key_code = self.scrcpy.ANDROID_KEYCODE_MAP.get(key_name, None)
        if self._keyboard_shown:
            self._poll_keyboard_input()
            if key_code == 67:
                self.scrcpy.send_keycode(key_code, 1)
            return True
        elif not self._keyboard_shown and key_code:
            self.scrcpy.send_keycode(key_code, 1)
            return True

        return False

    def _toggle_camera_mode(self, config):
        """Toggle camera mode (3D view control)."""
        if self._camera_active:
            # --- Exit camera mode ---
            self._camera_poll_stop.set()
            if self._camera_poll_thread and self._camera_poll_thread.is_alive():
                self._camera_poll_thread.join(timeout=1.0)
            self._camera_poll_thread = None

            self._camera_active = False
            if self.scrcpy._last_session:
                sw, sh = self.scrcpy._last_session
                self.scrcpy.send_touch(1, self._camera_touch_x, self._camera_touch_y, sw, sh)
            self._notify_camera_mode_change(False, None)
            return

        # --- Enter camera mode ---
        if not self.scrcpy._last_session:
            return
        sw, sh = self.scrcpy._last_session

        # Init Mouse
        try:
            mouse = Mouse()
            mw, mh = mouse.screen_width, mouse.screen_height
        except Exception:
            return
        self._camera_mouse = mouse

        cx = int(mw // 2)
        cy = int(mh // 2)
        self._camera_monitor_center = (cx, cy)
        self._camera_boundary_radius_sq = 200 * 100
        self._camera_last_mouse = (cx, cy)

        self._camera_active = True
        self._camera_config = config
        self._camera_center = (config.get('x', 0.5), config.get('y', 0.5))

        self._camera_screen_width = sw
        self._camera_screen_height = sh
        device_cx = int(self._camera_center[0] * sw)
        device_cy = int(self._camera_center[1] * sh)
        self._camera_touch_x = device_cx
        self._camera_touch_y = device_cy
        self.scrcpy.send_touch(0, device_cx, device_cy, sw, sh)

        # Start polling thread
        self._camera_poll_stop.clear()
        self._camera_poll_thread = threading.Thread(target=self._camera_poll_loop, daemon=True)
        self._camera_poll_thread.start()

        self._notify_camera_mode_change(True, {
            'center': self._camera_center,
            'sensitivity': self._camera_sensitivity
        })

    def _notify_camera_mode_change(self, active, data):
        """Notify frontend about camera mode state change."""
        # Call frontend function via webview through API
        if self.api:
            self.api.notify_camera_mode_change(active, data)

    def _camera_poll_loop(self):
        """Background thread: polls mouse position at 100Hz, sends touch deltas,
        and physically resets mouse to monitor center when boundary is exceeded."""
        mouse = self._camera_mouse
        cx, cy = self._camera_monitor_center
        r_sq = self._camera_boundary_radius_sq
        mw, mh = mouse.screen_width, mouse.screen_height
        last_mx, last_my = self._camera_last_mouse

        while not self._camera_poll_stop.is_set():
            try:
                mx, my = mouse.get_mouse_position()
            except Exception:
                time.sleep(0.005)
                continue

            dx = mx - last_mx
            dy = my - last_my
            last_mx, last_my = mx, my

            sens = self._camera_sensitivity
            sw = self._camera_screen_width
            sh = self._camera_screen_height

            # Scale monitor delta to device touch delta
            touch_dx = (dx / mw) * sw * sens if mw > 0 else 0
            touch_dy = (dy / mh) * sh * sens if mh > 0 else 0

            with self._camera_lock:
                new_tx = self._camera_touch_x + touch_dx
                new_ty = self._camera_touch_y + touch_dy
                clamped_tx = max(1, min(sw - 1, int(new_tx)))
                clamped_ty = max(1, min(sh - 1, int(new_ty)))
                self._camera_touch_x = clamped_tx
                self._camera_touch_y = clamped_ty

            if dx != 0 or dy != 0:
                self.scrcpy.send_touch(2, clamped_tx, clamped_ty, sw, sh)

            # Boundary check: distance from monitor center
            off_x = mx - cx
            off_y = my - cy
            if off_x * off_x + off_y * off_y > r_sq:
                # Lift touch
                self.scrcpy.send_touch(1, clamped_tx, clamped_ty, sw, sh)
                # Reset touch to device center
                center_tx = int(self._camera_center[0] * sw)
                center_ty = int(self._camera_center[1] * sh)
                with self._camera_lock:
                    self._camera_touch_x = center_tx
                    self._camera_touch_y = center_ty
                # Place touch at center
                self.scrcpy.send_touch(0, center_tx, center_ty, sw, sh)
                # Physically move mouse to monitor center
                try:
                    mouse.mouse_move(cx, cy, duration=0, steps=1)
                except Exception:
                    pass
                last_mx, last_my = cx, cy

            time.sleep(0.01)

    def reset(self):
        """Reset all active key states and release pointers."""
        # Stop camera polling thread first
        self._camera_poll_stop.set()
        if self._camera_poll_thread and self._camera_poll_thread.is_alive():
            self._camera_poll_thread.join(timeout=1.0)
        self._camera_poll_thread = None
        self._camera_mouse = None

        # Stop keyboard polling thread
        self._kb_poll_stop.set()
        if self._kb_poll_thread and self._kb_poll_thread.is_alive():
            self._kb_poll_thread.join(timeout=1.0)
        self._kb_poll_thread = None
        self._kb_poll_started = False

        self._down_state_keys.clear()
        self._dpad_states.clear()
        # Also reset camera state
        self._camera_active = False
        self._camera_config = None
        self._camera_center = (0.5, 0.5)
        self._camera_touch_x = 0
        self._camera_touch_y = 0
        self._camera_screen_width = 0
        self._camera_screen_height = 0
        self._camera_sensitivity = 1.0
        self._camera_monitor_center = (0, 0)
        self._camera_last_mouse = (0, 0)
        if self.scrcpy:
            self.scrcpy.key_mapping_reset()

    # -- Phone keyboard polling --

    @property
    def keyboard_shown(self) -> bool | None:
        return self._keyboard_shown

    def read_and_clear_just_hidden(self) -> bool:
        val = self._keyboard_just_hidden
        self._keyboard_just_hidden = False
        return val

    def _start_keyboard_poll(self):
        if self._kb_poll_started:
            return
        self._kb_poll_started = True
        self._kb_poll_stop.clear()
        self._kb_poll_thread = threading.Thread(target=self._keyboard_poll_loop, daemon=True)
        self._kb_poll_thread.start()

    def _keyboard_poll_loop(self):
        while not self._kb_poll_stop.is_set():
            time.sleep(0.1)
            output = self.scrcpy.adb_shell("dumpsys", "input_method")
            shown = None
            if output is not None:
                m = re.search(r"mInputShown=(true|false)", output)
                if m:
                    shown = m.group(1) == "true"
            if shown is not None:
                prev = self._keyboard_shown
                self._keyboard_shown = shown
                if prev is True and shown is False:
                    self._keyboard_just_hidden = True
                    if self.api and self._last_notify_state != (False, True):
                        self.api._notify_keyboard_state(False, True)
                        self._last_notify_state = (False, True)
                elif prev is not True and shown is True:
                    if self.api and self._last_notify_state != (True, False):
                        self.api._notify_keyboard_state(True, False)
                        self._last_notify_state = (True, False)

    def _poll_keyboard_input(self):
        try:
            if not self.window:
                return
            js = "document.querySelector('.ime-input')?.value || ''"
            cur = self.window.evaluate_js(js)
            if cur:
                self.scrcpy.send_text(''.join(cur))
                self.window.evaluate_js("window.__clearImeInput?.()")
        except Exception:
            pass

    def set_focus_state(self, focused):
        if not focused and self._enabled:
            self._enabled_before_focus = self._enabled
            self._enabled = False
            self.reset()
        elif focused and not self._enabled and self._enabled_before_focus:
            self._enabled = True

    def has_mleft_key_configured(self):
        """检查当前键位映射是否有任何控件配置了MLeft键"""
        if not self._active_mapping:
            return False

        # 检查所有类型的控件
        for ctrl in self._active_mapping.get("controls", []):
            if ctrl.get("key") == "MLeft":
                return True

        for swp in self._active_mapping.get("swipes", []):
            if swp.get("key") == "MLeft":
                return True

        for dpad in self._active_mapping.get("dpad", []):
            for _, info in dpad.get("keys", {}).items():
                if info.get("key") == "MLeft":
                    return True

        for cam in self._active_mapping.get("camera", []):
            if cam.get("key") == "MLeft":
                return True

        return False
