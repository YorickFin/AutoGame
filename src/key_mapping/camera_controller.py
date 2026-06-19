"""Camera controller for 3D view mode with raw-input-based mouse look control.

Uses RAWINPUT to read unbounded relative mouse deltas from the hardware,
eliminating the need for cursor warping or boundary detection.

Also locks mouse cursor to screen center and hides it during camera mode.

Supports both global (toggle-based, center touch) and local (hold-based,
button-position touch) camera controls in one unified class.
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
    """Controls 3D view mode via raw mouse deltas sent as touch deltas.

    Manages both global (toggle, center-based) and local (hold, position-based)
    camera modes.  Two poll threads share the same RawInputListener; the local
    mode pauses the global thread while active.
    """

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

        # Local camera state (single-key, no concurrency)
        self._local_active = threading.Event()       # set when local is taking over
        self._local_config: Optional[dict] = None     # config of active local camera
        self._local_pointer_id: Optional[int] = None  # pointer_id for local touch
        self._local_tx: int = 0                       # local touch x (pixels)
        self._local_ty: int = 0                       # local touch y (pixels)
        self._local_poll_thread: Optional[threading.Thread] = None
        self._local_poll_stop = threading.Event()
        self._global_release_event = threading.Event()  # global confirms pointer released

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

        # Start raw input listener
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
        self._local_active.clear()

        self._stop_local_poll_loop()

        if not self._active:
            return

        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
        self._poll_thread = None

        if self._scrcpy_manager._last_session and self._pointer_id is not None:
            self._scrcpy_manager.send_normalized_touch(1, self._center[0], self._center[1],
                                                       pointer_id=self._pointer_id)
            self._pointer_id = None

        # Stop raw input listener
        self._raw_input.stop()

        # Release any waiting local thread
        self._global_release_event.set()
        self._global_release_event.clear()

        self._unlock_mouse()

        self._active = False
        self._config = None
        self._local_config = None
        self._local_pointer_id = None

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
        self._local_active.clear()
        self._global_release_event.clear()

    def notify_state_change(self, api):
        """Notify frontend about camera mode state change."""
        if api:
            api.notify_camera_mode_change(self._active, {
                'center': self._center,
                'sensitivity': self._sensitivity
            } if self._active else None)

    # ── Local camera control ──────────────────────────────────────────

    def on_camera_local_down(self, config: dict) -> bool:
        """Handle local camera key-down (hold-based, position-specific).

        Requires global camera to already be active.
        Returns True if the event was consumed.
        """
        if not self._active:
            return False

        if self._local_active.is_set():
            # Only one local at a time
            return False

        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            return False

        self._local_config = config
        self._local_active.set()

        # Wait for global poll_loop to release its pointer
        self._global_release_event.wait(timeout=1.0)
        self._global_release_event.clear()

        time.sleep(0.03)

        # Choose a pointer_id that differs from the (now-released) global one
        local_pid = 9 if (self._pointer_id is None or self._pointer_id != 9) else 8
        lx, ly = config['x'], config['y']
        resp = self._scrcpy_manager.send_normalized_touch(0, lx, ly, pointer_id=local_pid)
        if not resp.get("ok"):
            return True

        pid = resp.get("pointer_id")
        if pid is None:
            return True

        self._local_pointer_id = pid
        self._local_tx = int(lx * sw)
        self._local_ty = int(ly * sh)
        self._start_local_poll_loop()

        return True

    def on_camera_local_up(self, config: dict) -> bool:
        """Handle local camera key-up."""
        if not self._local_active.is_set():
            return False

        self._local_active.clear()

        # Send local UP
        if self._local_pointer_id is not None and self._scrcpy_manager._last_session:
            sw, sh = self._scrcpy_manager._last_session
            lx, ly = self._local_config['x'], self._local_config['y']
            self._scrcpy_manager.send_normalized_touch(1, lx, ly, pointer_id=self._local_pointer_id)

        self._stop_local_poll_loop()
        self._local_config = None
        self._local_pointer_id = None
        return True

    def _start_local_poll_loop(self):
        """Start the local poll thread."""
        if self._local_poll_thread and self._local_poll_thread.is_alive():
            return
        self._local_poll_stop.clear()
        self._local_poll_thread = threading.Thread(target=self._local_poll_loop, daemon=True)
        self._local_poll_thread.start()

    def _stop_local_poll_loop(self):
        """Stop the local poll thread."""
        if self._local_poll_thread and self._local_poll_thread.is_alive():
            self._local_poll_stop.set()
            self._local_poll_thread.join(timeout=1.0)
        self._local_poll_thread = None

    def _local_poll_loop(self):
        """Poll loop for local camera: reads raw deltas and moves the local touch point."""
        raw = self._raw_input
        sens = self._sensitivity
        sw, sh = self._scrcpy_manager._last_session
        if not sw or not sh:
            return

        while not self._local_poll_stop.is_set():
            dx, dy = raw.read_deltas()
            if dx == 0 and dy == 0:
                time.sleep(0.01)
                continue

            pixel_dx = dx * sens
            pixel_dy = dy * sens

            new_tx = self._local_tx + pixel_dx
            new_ty = self._local_ty + pixel_dy
            clamped_tx = max(1, min(sw - 1, int(new_tx)))
            clamped_ty = max(1, min(sh - 1, int(new_ty)))
            self._local_tx = clamped_tx
            self._local_ty = clamped_ty

            self._scrcpy_manager.send_normalized_touch(
                2, clamped_tx / sw, clamped_ty / sh, pointer_id=self._local_pointer_id,
            )

            time.sleep(0.01)

    # ── Global poll loop ──────────────────────────────────────────────

    def _poll_loop(self):
        """Background thread: reads raw deltas and sends touch deltas.

        When local camera is active, releases the global pointer and sleeps.
        When local camera releases, recreates the center touch point.
        """
        sw = self._screen_width
        sh = self._screen_height
        sens = self._sensitivity
        raw = self._raw_input

        while not self._poll_stop.is_set():

            # ---- Local camera takes precedence ----
            if self._local_active.is_set():
                if self._pointer_id is not None:
                    # Release global touch point so local can use its own
                    self._scrcpy_manager.send_normalized_touch(
                        1, self._touch_x / sw, self._touch_y / sh, pointer_id=self._pointer_id,
                    )
                    self._pointer_id = None
                    self._global_release_event.set()
                time.sleep(0.01)
                continue

            # ---- If pointer was released by local, recreate at center ----
            if self._pointer_id is None:
                self._touch_x = int(self._center[0] * sw)
                self._touch_y = int(self._center[1] * sh)
                resp = self._scrcpy_manager.send_normalized_touch(0, self._center[0], self._center[1])
                if resp.get("ok"):
                    self._pointer_id = resp.get("pointer_id")

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
