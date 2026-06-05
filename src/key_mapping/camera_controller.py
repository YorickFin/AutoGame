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
        self._scrcpy_manager.send_touch(0, device_cx, device_cy, screen_width, screen_height)

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

        if self._scrcpy_manager._last_session:
            sw, sh = self._scrcpy_manager._last_session
            self._scrcpy_manager.send_touch(1, self._touch_x, self._touch_y, sw, sh)

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
                self._scrcpy_manager.send_touch(2, clamped_tx, clamped_ty, sw, sh)

            off_x = mx - cx
            off_y = my - cy
            if off_x * off_x + off_y * off_y > r_sq:
                self._scrcpy_manager.send_touch(1, clamped_tx, clamped_ty, sw, sh)
                center_tx = int(self._center[0] * sw)
                center_ty = int(self._center[1] * sh)
                with self._lock:
                    self._touch_x = center_tx
                    self._touch_y = center_ty
                self._scrcpy_manager.send_touch(0, center_tx, center_ty, sw, sh)
                try:
                    mouse.mouse_move(cx, cy, duration=0, steps=1)
                except Exception:
                    pass
                last_mx, last_my = cx, cy

            time.sleep(0.01)
