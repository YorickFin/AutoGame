"""Key mapping executor that orchestrates button mapping, input detection, and camera control."""

from __future__ import annotations

import logging

from .button_mapping import ButtonMapping
from .camera_controller import CameraController, LocalCameraController
from .input_detector import InputDetector
from ..services import services

logger = logging.getLogger(__name__)


class KeyMapping:
    """Main executor that coordinates button mapping, input detection, and camera control."""

    def __init__(self):
        self._button_mapping = ButtonMapping()
        self._camera = CameraController()
        self._local_camera = LocalCameraController(self._camera)
        self._input = InputDetector()
        self._enabled = False
        self._enabled_before_focus = False
        self._active_mapping = None

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    @property
    def _api(self):
        try:
            return services.api
        except AttributeError:
            return None

    def apply(self, mapping_data):
        self._active_mapping = mapping_data
        self._enabled = True
        sensitivity = mapping_data.get('cameraSensitivity', 1.0)
        self._camera._sensitivity = sensitivity
        self._button_mapping.apply(mapping_data)
        self._input.start()

    def remove(self):
        self.reset()
        self._active_mapping = None
        self._enabled = False
        self._button_mapping.remove()
        self._input.reset()

    @property
    def enabled(self):
        return self._enabled and self._active_mapping is not None

    def get_mapped_keys(self):
        keys = self._button_mapping.get_mapped_keys()
        if self._active_mapping:
            for cam_local in self._active_mapping.get("cameras_local", []):
                k = cam_local.get("key")
                if k:
                    keys.add(k)
        return keys

    def on_key_down(self, key_name):
        """Handle key press - delegate to appropriate module."""
        if not self._enabled or not self._active_mapping:
            return False

        # Handle input keycodes
        key_code = self._scrcpy_manager.ANDROID_KEYCODE_MAP.get(key_name, None)
        if self._input.input_shown:
            if key_code in (62, 66, 67):
                self._scrcpy_manager.send_keycode(key_code, 0)
            return True
        elif not self._input.input_shown:
            if key_code:
                self._scrcpy_manager.send_keycode(key_code, 0)

        # Check camera controls first (toggle mode)
        for cam in self._active_mapping.get("camera", []):
            if cam.get("key") == key_name:
                self._toggle_camera_mode(cam)
                return True

        # Check local camera controls (temporary local view control)
        for cam_local in self._active_mapping.get("cameras_local", []):
            if cam_local.get("key") == key_name:
                self._local_camera.on_key_down(cam_local)
                return True  # Always consume the event to prevent repeat triggers

        # Let button mapping handle controls, swipes, dpad
        if self._button_mapping.on_key_down(key_name):
            return True

        return False

    def on_key_up(self, key_name):
        """Handle key release - delegate to appropriate module."""
        if not self._enabled or not self._active_mapping:
            return False

        # Handle input keycodes
        key_code = self._scrcpy_manager.ANDROID_KEYCODE_MAP.get(key_name, None)
        if self._input.input_shown:
            if self._api:
                self._api.poll_input()
            if key_code in (62, 66, 67):
                self._scrcpy_manager.send_keycode(key_code, 1)
            return True
        elif not self._input.input_shown:
            if key_code:
                self._scrcpy_manager.send_keycode(key_code, 1)

        # Let button mapping handle controls and dpad
        if self._button_mapping.on_key_up(key_name):
            return True

        # Handle local camera controls
        for cam_local in self._active_mapping.get("cameras_local", []):
            if cam_local.get("key") == key_name:
                if self._local_camera.on_key_up(cam_local):
                    return True

        return False

    def _toggle_camera_mode(self, config):
        """Toggle camera mode (3D view control)."""
        if self._camera.active:
            self._camera.stop()
            self._camera.notify_state_change(self._api)
        else:
            if not self._scrcpy_manager._last_session:
                return
            sw, sh = self._scrcpy_manager._last_session
            self._camera.start(config, sw, sh, self._camera._sensitivity)
            self._camera.notify_state_change(self._api)

    def reset(self):
        """Reset all active key states and release pointers."""
        self._camera.reset()
        self._local_camera.reset()
        self._input.reset()
        self._button_mapping.reset()
        if self._scrcpy_manager:
            self._scrcpy_manager.key_mapping_reset()

    @property
    def input_shown(self):
        return self._input.input_shown

    def read_and_clear_just_hidden(self):
        return self._input.read_and_clear_just_hidden()

    def set_focus_state(self, focused):
        if not focused and self._enabled:
            self._enabled_before_focus = self._enabled
            self._enabled = False
            self.reset()
        elif focused and not self._enabled and self._enabled_before_focus:
            self._enabled = True

    def has_mleft_key_configured(self):
        return self._button_mapping.has_mleft_key_configured()
