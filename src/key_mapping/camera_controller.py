"""Camera controller for 3D view mode with mouse-based look control."""

from __future__ import annotations

import threading
import time
from ..services import services
from autoxkit.mousekey.mouse import Mouse


class CameraController:
    """Controls 3D view mode by polling mouse position and sending touch deltas."""

    def __init__(self):
        self._active = False
        self._config = None
        self._center = (0.5, 0.5)
        self._touch_x = 0
        self._touch_y = 0
        self._screen_width = 0
        self._screen_height = 0
        self._sensitivity = 1.0
        self._mouse = None
        self._monitor_center = (0, 0)
        self._boundary_radius_sq = 100 * 100
        self._last_mouse = (0, 0)
        self._poll_thread = None
        self._poll_stop = threading.Event()
        self._lock = threading.Lock()
        self._pointer_id: int | None = None

    @property
    def active(self) -> bool:
        return self._active

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    @property
    def _position(self):
        return services.position

    def start(self, config: dict, screen_width: int, screen_height: int, sensitivity: float):
        """Enter camera mode with given configuration."""
        if self._active:
            return

        if not self._scrcpy_manager._last_session:
            return

        try:
            mouse = Mouse()
        except Exception:
            return

        self._mouse = mouse
        mw, mh = mouse.screen_width, mouse.screen_height
        cx = int(mw // 2)
        cy = int(mh // 2)
        self._monitor_center = (cx, cy)
        self._last_mouse = (cx, cy)

        self._active = True
        self._config = config
        self._center = (config.get('x', 0.5), config.get('y', 0.5))
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._boundary_radius_sq = ((mh - 10) // 2) * ((mh - 10) // 2)
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

        self._active = False
        self._config = None

    def reset(self):
        """Reset all camera state."""
        self.stop()
        self._mouse = None
        self._center = (0.5, 0.5)
        self._touch_x = 0
        self._touch_y = 0
        self._screen_width = 0
        self._screen_height = 0
        self._sensitivity = 1.0
        self._monitor_center = (0, 0)
        self._last_mouse = (0, 0)
        self._pointer_id = None

    def notify_state_change(self, api):
        """Notify frontend about camera mode state change."""
        if api:
            api.notify_camera_mode_change(self._active, {
                'center': self._center,
                'sensitivity': self._sensitivity
            } if self._active else None)

    def _poll_loop(self):
        """Background thread: polls mouse position at 100Hz and sends touch deltas."""
        mouse = self._mouse
        if not mouse:
            return

        cx, cy = self._monitor_center
        r_sq = self._boundary_radius_sq
        mw, mh = mouse.screen_width, mouse.screen_height
        last_mx, last_my = self._last_mouse
        sw = self._screen_width
        sh = self._screen_height
        sens = self._sensitivity
        pid = self._pointer_id

        while not self._poll_stop.is_set():
            try:
                mx, my = self._position
            except Exception:
                time.sleep(0.005)
                continue

            dx = mx - last_mx
            dy = my - last_my
            last_mx, last_my = mx, my

            touch_dx = (dx / mw) * sw * sens if mw > 0 else 0
            touch_dy = (dy / mh) * sh * sens if mh > 0 else 0

            with self._lock:
                new_tx = self._touch_x + touch_dx
                new_ty = self._touch_y + touch_dy
                clamped_tx = max(1, min(sw - 1, int(new_tx)))
                clamped_ty = max(1, min(sh - 1, int(new_ty)))
                self._touch_x = clamped_tx
                self._touch_y = clamped_ty

            if dx != 0 or dy != 0:
                self._scrcpy_manager.send_normalized_touch(2, clamped_tx / sw, clamped_ty / sh, pointer_id=pid)

            off_x = mx - cx
            off_y = my - cy
            if off_x * off_x + off_y * off_y > r_sq:
                center_tx = int(self._center[0] * sw)
                center_ty = int(self._center[1] * sh)
                self._scrcpy_manager.send_normalized_touch(1, self._center[0], self._center[1], pointer_id=pid)
                mouse.mouse_move(cx, cy, duration=0, steps=1)
                with self._lock:
                    self._touch_x = center_tx
                    self._touch_y = center_ty
                self._scrcpy_manager.send_normalized_touch(0, self._center[0], self._center[1])
                last_mx, last_my = cx, cy

            time.sleep(0.01)


class LocalCameraController:
    """局部3D视角控制 - 以按钮位置为基准进行触摸操作。

    只有在全局 CameraController 开启时才生效。
    按下绑定键时：在按钮位置 dn-touch（新增独立的触摸点）
    弹起绑定键时：局部 up-touch（不干扰全局）
    """

    def __init__(self, global_controller: CameraController):
        self._global = global_controller
        self._down_keys: dict[str, tuple[int, int, int]] = {}  # key -> (pointer_id, touch_x, touch_y)
        self._mouse = None
        self._poll_thread = None
        self._poll_stop = threading.Event()
        self._lock = threading.Lock()

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    @property
    def _position(self):
        return services.position

    @property
    def has_active_local(self) -> bool:
        """是否有活跃的局部控制"""
        return len(self._down_keys) > 0

    def _is_any_key_down(self) -> bool:
        """检查是否有按键处于按下状态"""
        return len(self._down_keys) > 0

    def on_key_down(self, config: dict) -> bool:
        """按下绑定键：在局部位置 dn-touch（不干扰全局）"""
        if not self._global.active:
            return False  # 全局未开启，局部不生效

        key_name = config.get("key")
        if not key_name or key_name in self._down_keys:
            return False

        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            return False

        # 在按钮位置 dn-touch（使用 send_normalized_touch 获取 pointer_id）
        lx = config['x']
        ly = config['y']
        resp = self._scrcpy_manager.send_normalized_touch(0, lx, ly)

        if not resp.get("ok"):
            return True

        pid = resp.get("pointer_id")
        if pid is None:
            return True

        self._down_keys[key_name] = (pid, int(lx * sw), int(ly * sh))

        # 启动局部 poll_loop（如果还没有）
        if not self._poll_thread or not self._poll_thread.is_alive():
            self._start_poll_loop()

        return True

    def _start_poll_loop(self):
        """启动局部控制的鼠标轮询"""
        if self._poll_thread and self._poll_thread.is_alive():
            return

        try:
            self._mouse = Mouse()
        except Exception:
            self._mouse = None
            return

        self._poll_stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        """局部控制的鼠标轮询：跟随鼠标移动触摸点"""
        mouse = self._mouse
        if not mouse:
            return

        mw, mh = mouse.screen_width, mouse.screen_height
        if mw <= 0 or mh <= 0:
            return

        cx, cy = mouse.screen_width // 2, mouse.screen_height // 2
        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            return

        last_mx, last_my = cx, cy

        while not self._poll_stop.is_set():
            try:
                mx, my = self._position
            except Exception:
                time.sleep(0.005)
                continue

            dx = mx - last_mx
            dy = my - last_my
            last_mx, last_my = mx, my

            if dx == 0 and dy == 0:
                time.sleep(0.01)
                continue

            touch_dx = (dx / mw) * sw * self._global._sensitivity
            touch_dy = (dy / mh) * sh * self._global._sensitivity

            with self._lock:
                if not self._down_keys:
                    continue

                # 更新所有活跃的局部触摸点
                new_states = {}
                for key_name, (pid, tx, ty) in self._down_keys.items():
                    new_tx = tx + touch_dx
                    new_ty = ty + touch_dy
                    clamped_tx = max(1, min(sw - 1, int(new_tx)))
                    clamped_ty = max(1, min(sh - 1, int(new_ty)))
                    new_states[key_name] = (pid, clamped_tx, clamped_ty)
                    self._scrcpy_manager.send_normalized_touch(2, clamped_tx / sw, clamped_ty / sh, pointer_id=pid)

                # 写回状态
                self._down_keys.clear()
                self._down_keys.update(new_states)

            time.sleep(0.01)

    def on_key_up(self, config: dict) -> bool:
        """弹起绑定键：局部 up-touch（不干扰全局）"""
        key_name = config.get("key")
        item = self._down_keys.pop(key_name, None)
        if item is None:
            return False

        pid, lx, ly = item
        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            self._down_keys.clear()
            return True

        # 局部 up-touch（不恢复全局，因为全局的 _poll_loop 一直在运行）
        self._scrcpy_manager.send_normalized_touch(1, lx / sw, ly / sh, pointer_id=pid)

        if not self._down_keys:
            self._stop_poll_loop()

        return True

    def _stop_poll_loop(self):
        """停止局部控制的鼠标轮询"""
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_stop.set()
            self._poll_thread.join(timeout=1.0)
        self._poll_thread = None

    def reset(self):
        """重置所有状态"""
        self._stop_poll_loop()
        self._down_keys.clear()
        self._mouse = None
