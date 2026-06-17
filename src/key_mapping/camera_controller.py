"""Camera controller for 3D view mode with raw-input-based mouse look control.

Uses RAWINPUT to read unbounded relative mouse deltas from the hardware,
eliminating the need for cursor warping or boundary detection.

Also locks mouse cursor to screen center and hides it during camera mode.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import threading
import time
from typing import Optional

from ..services import services
from .raw_input_listener import RawInputListener

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

OCR_NORMAL = 32512
SPI_SETCURSORS = 0x0057

user32.CreateCursor.argtypes = [
    ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int,
    ctypes.c_char_p, ctypes.c_char_p
]
user32.CreateCursor.restype = ctypes.c_void_p

user32.SetSystemCursor.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.SetSystemCursor.restype = ctypes.c_int

user32.SystemParametersInfoW.argtypes = [
    ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint
]
user32.SystemParametersInfoW.restype = ctypes.c_int

user32.ClipCursor.argtypes = [ctypes.POINTER(ctypes.wintypes.RECT)]
user32.ClipCursor.restype = ctypes.c_int

class CameraController:
    """Controls 3D view mode via raw mouse deltas sent as touch deltas."""

    def __init__(self):
        self._active = False
        self._config = None
        self._center = (0.5, 0.5)
        self._touch_x = 0
        self._touch_y = 0
        self._screen_width = 0
        self._screen_height = 0
        self._sensitivity = 1.0
        self._poll_thread = None
        self._poll_stop = threading.Event()
        self._pointer_id: Optional[int] = None
        self._local_touch_active = False
        self._prev_local_touch_active = False  # 用于检测 _local_touch_active 的边沿变化

        # Raw input listener for unbounded mouse deltas
        self._raw_input = RawInputListener()

        # Mouse lock/hide state
        self._mouse_locked = False
        self._screen_center = (0, 0)
        self._sys_cursors_hidden = False


    @property
    def active(self) -> bool:
        return self._active

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    def _create_blank_cursor(self) -> int:
        """Create a fully transparent cursor."""
        cx = user32.GetSystemMetrics(13)  # SM_CXCURSOR
        cy = user32.GetSystemMetrics(14)  # SM_CYCURSOR

        bytes_per_line = ((cx + 15) // 16) * 2
        plane_size = bytes_per_line * cy

        and_plane = bytes([0xFF] * plane_size)
        xor_plane = bytes([0x00] * plane_size)

        return user32.CreateCursor(
            kernel32.GetModuleHandleW(None),
            cx // 2, cy // 2,
            cx, cy,
            and_plane, xor_plane
        )

    def _hide_system_cursors(self):
        """Replace system cursors with blank ones."""
        if self._sys_cursors_hidden:
            return

        cursor_ids = [OCR_NORMAL]

        for cursor_id in cursor_ids:
            h_blank = self._create_blank_cursor()
            if h_blank:
                user32.SetSystemCursor(h_blank, cursor_id)

        self._sys_cursors_hidden = True

    def _restore_system_cursors(self):
        """Restore original system cursors."""
        if not self._sys_cursors_hidden:
            return

        if services.macro.set_cursor_flag:
            services.macro.set_mouse_icon()
            self._sys_cursors_hidden = False
        else:
            user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            self._sys_cursors_hidden = False

    def _lock_mouse(self):
        """Lock mouse cursor to screen center, hide it, and clip cursor."""
        if self._mouse_locked:
            return

        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        self._screen_center = (screen_width // 2, screen_height // 2)

        user32.SetCursorPos(self._screen_center[0], self._screen_center[1])

        clip_rect = ctypes.wintypes.RECT()
        clip_rect.left = self._screen_center[0]
        clip_rect.top = self._screen_center[1]
        clip_rect.right = self._screen_center[0] + 1
        clip_rect.bottom = self._screen_center[1] + 1
        user32.ClipCursor(ctypes.byref(clip_rect))

        self._hide_system_cursors()

        self._mouse_locked = True
        logger.debug("Mouse locked to screen center")

    def _unlock_mouse(self):
        """Restore mouse cursor visibility, position, and release clip."""
        if not self._mouse_locked:
            return

        user32.ClipCursor(None)

        self._restore_system_cursors()

        user32.SetCursorPos(self._screen_center[0], self._screen_center[1])

        self._mouse_locked = False
        logger.debug("Mouse unlocked")

    def start(self, config: dict, screen_width: int, screen_height: int, sensitivity: float):
        """Enter camera mode with given configuration."""
        if self._active:
            return

        if not self._scrcpy_manager._last_session:
            return

        # Start raw input listener (captures hardware mouse deltas,
        # no boundary / no warp needed)
        if not self._raw_input.start():
            logger.warning("RawInputListener failed to start, camera mode unavailable")
            return

        self._lock_mouse()

        self._active = True
        self._config = config
        self._center = (config.get('x', 0.5), config.get('y', 0.5))
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._sensitivity = sensitivity

        device_cx = int(self._center[0] * screen_width)
        device_cy = int(self._center[1] * screen_height)
        self._touch_x = device_cx
        self._touch_y = device_cy

        resp = self._scrcpy_manager.send_normalized_touch(0, self._center[0], self._center[1])
        if resp.get("ok"):
            self._pointer_id = resp.get("pointer_id")

        self._poll_stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self):
        """Exit camera mode."""
        if not self._active:
            return

        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
        self._poll_thread = None

        if self._scrcpy_manager._last_session and self._pointer_id is not None:
            self._scrcpy_manager.send_normalized_touch(1, self._center[0], self._center[1], pointer_id=self._pointer_id)
            self._pointer_id = None

        # Stop raw input listener
        self._raw_input.stop()

        self._unlock_mouse()

        self._active = False
        self._config = None
        self._local_touch_active = False
        self._prev_local_touch_active = False

    def reset(self):
        """Reset all camera state."""
        self.stop()
        self._center = (0.5, 0.5)
        self._touch_x = 0
        self._touch_y = 0
        self._screen_width = 0
        self._screen_height = 0
        self._sensitivity = 1.0
        self._pointer_id = None
        self._mouse_locked = False
        self._screen_center = (0, 0)
        self._local_touch_active = False
        self._prev_local_touch_active = False


    def notify_state_change(self, api):
        """Notify frontend about camera mode state change."""
        if api:
            api.notify_camera_mode_change(self._active, {
                'center': self._center,
                'sensitivity': self._sensitivity
            } if self._active else None)

    def _poll_loop(self):
        """Background thread: reads raw deltas and sends touch deltas.

        No boundary detection or cursor warping needed -- RAWINPUT
        provides unbounded relative deltas directly from the hardware.
        """
        sw = self._screen_width
        sh = self._screen_height
        sens = self._sensitivity
        raw = self._raw_input
        # 同步局部状态追踪变量，防止启动前已被设置
        prev_local = self._local_touch_active

        while not self._poll_stop.is_set():

            # ---- 检测局部触摸状态变化边沿（每轮都执行，不依赖 deltas）----
            if self._local_touch_active and not prev_local:
                # 上升沿：局部接管 → 释放全局触摸点
                if self._pointer_id is not None:
                    self._scrcpy_manager.send_normalized_touch(
                        1, self._touch_x / sw, self._touch_y / sh, pointer_id=self._pointer_id,
                    )
                    self._pointer_id = None
            elif not self._local_touch_active and prev_local:
                # 下降沿：局部释放 → 在中心重新建立全局触摸点
                self._touch_x = int(self._center[0] * sw)
                self._touch_y = int(self._center[1] * sh)
                resp = self._scrcpy_manager.send_normalized_touch(0, self._center[0], self._center[1])
                if resp.get("ok"):
                    self._pointer_id = resp.get("pointer_id")

            prev_local = self._local_touch_active
            self._prev_local_touch_active = self._local_touch_active

            # 局部激活时跳过 read_deltas，让局部 poll_loop 消费
            if self._local_touch_active:
                time.sleep(0.01)
                continue

            dx, dy = raw.read_deltas()
            if dx == 0 and dy == 0:
                time.sleep(0.01)
                continue

            touch_dx = dx * sens
            touch_dy = dy * sens

            new_tx = self._touch_x + touch_dx
            new_ty = self._touch_y + touch_dy

            need_recreate = (new_tx < 1 or new_tx >= sw or new_ty < 1 or new_ty >= sh)
            if need_recreate:
                old_pointer_id = self._pointer_id
                touch_x = self._touch_x
                touch_y = self._touch_y

            if need_recreate:
                self._scrcpy_manager.send_normalized_touch(
                    1, touch_x / sw, touch_y / sh, pointer_id=old_pointer_id,
                )

                center_x = int(self._center[0] * sw)
                center_y = int(self._center[1] * sh)
                resp = self._scrcpy_manager.send_normalized_touch(0, self._center[0], self._center[1])
                if resp.get("ok"):
                    self._pointer_id = resp.get("pointer_id")
                self._touch_x = center_x
                self._touch_y = center_y

                self._scrcpy_manager.send_normalized_touch(
                    2, self._touch_x / sw, self._touch_y / sh, pointer_id=self._pointer_id,
                )
            else:
                self._touch_x = int(new_tx)
                self._touch_y = int(new_ty)

                self._scrcpy_manager.send_normalized_touch(
                    2, self._touch_x / sw, self._touch_y / sh, pointer_id=self._pointer_id,
                )

            time.sleep(0.01)

class LocalCameraController:
    """局部3D视角控制 - 以按钮位置为基准进行触摸操作。

    只有在全局 CameraController 开启时才生效。
    按下绑定键时：在按钮位置 dn-touch（新增独立的触摸点）
    弹起绑定键时：局部 up-touch（不干扰全局）
    """

    def __init__(self):
        self._down_keys: dict[str, tuple[int, int, int]] = {}  # key -> (pointer_id, touch_x, touch_y)
        self._poll_thread = None
        self._poll_stop = threading.Event()
        self._lock = threading.Lock()

    @property
    def _global_camera(self):
        return services.camera_controller

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager


    @property
    def has_active_local(self) -> bool:
        """是否有活跃的局部控制"""
        return len(self._down_keys) > 0

    def _is_any_key_down(self) -> bool:
        """检查是否有按键处于按下状态"""
        return len(self._down_keys) > 0

    def on_key_down(self, config: dict) -> bool:
        """按下绑定键：在局部位置 dn-touch（不干扰全局）"""
        if not self._global_camera.active:
            return False  # 全局未开启，局部不生效

        key_name = config.get("key")
        if not key_name:
            return False


        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            return False

        lx = config['x']
        ly = config['y']

        with self._lock:
            if key_name in self._down_keys:
                return False

        # 先发局部 DN，再通知全局释放触摸点（保证 DN 先于 UP 到达）
        resp = self._scrcpy_manager.send_normalized_touch(0, lx, ly)
        if not resp.get("ok"):
            return True

        pid = resp.get("pointer_id")
        if pid is None:
            return True

        with self._lock:
            self._down_keys[key_name] = (pid, int(lx * sw), int(ly * sh))
            self._global_camera._local_touch_active = True

        # 启动局部 poll_loop（如果还没有）
        if not self._poll_thread or not self._poll_thread.is_alive():
            self._start_poll_loop()

        return True

    def _start_poll_loop(self):
        """启动局部控制的鼠标轮询"""
        if self._poll_thread and self._poll_thread.is_alive():
            return


        self._poll_stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        """局部控制的鼠标轮询：使用原始鼠标增量数据"""
        raw = self._global_camera._raw_input
        sens = self._global_camera._sensitivity
        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            return

        while not self._poll_stop.is_set():
            dx, dy = raw.read_deltas()
            if dx == 0 and dy == 0:
                time.sleep(0.01)
                continue

            pixel_dx = dx * sens
            pixel_dy = dy * sens

            with self._lock:
                if not self._down_keys:
                    continue

                snapshot = {}
                for key_name, (pid, tx, ty) in self._down_keys.items():
                    new_tx = tx + pixel_dx
                    new_ty = ty + pixel_dy
                    clamped_tx = max(1, min(sw - 1, int(new_tx)))
                    clamped_ty = max(1, min(sh - 1, int(new_ty)))
                    snapshot[key_name] = (pid, clamped_tx, clamped_ty)

                self._down_keys.clear()
                self._down_keys.update(snapshot)

            # 锁外发送 MOVE，避免 I/O 阻塞状态更新
            for key_name, (pid, clamped_tx, clamped_ty) in snapshot.items():
                self._scrcpy_manager.send_normalized_touch(2, clamped_tx / sw, clamped_ty / sh, pointer_id=pid)

            time.sleep(0.01)

    def on_key_up(self, config: dict) -> bool:
        """弹起绑定键：局部 up-touch（不干扰全局）"""
        key_name = config.get("key")
        with self._lock:
            item = self._down_keys.pop(key_name, None)
            if item is None:
                return False

        pid, lx, ly = item
        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            with self._lock:
                self._down_keys.clear()
            return True

        # 局部 up-touch（不恢复全局，因为全局的 _poll_loop 已经在下降沿处理）
        self._scrcpy_manager.send_normalized_touch(1, lx / sw, ly / sh, pointer_id=pid)

        with self._lock:
            if not self._down_keys:
                self._global_camera._local_touch_active = False
                should_stop = True
            else:
                should_stop = False

        if should_stop:
            self._stop_poll_loop()

        return True

    def _stop_poll_loop(self):
        """停止局部控制的原始输入轮询"""
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_stop.set()
            self._poll_thread.join(timeout=1.0)
        self._poll_thread = None

    def reset(self):
        """重置所有状态"""
        self._stop_poll_loop()
        self._down_keys.clear()
