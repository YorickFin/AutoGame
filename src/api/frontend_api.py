import ctypes
import logging

from ..services import services


logger = logging.getLogger(__name__)


class FrontendApi:

    @property
    def _window(self):
        return services.window

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    def _is_window_valid(self):
        window = self._window
        if not window:
            return False
        try:
            if hasattr(window, '_impl') and hasattr(window._impl, 'webview'):
                if ctypes.c_long(window._impl.webview.IsDisposed).value != 0:
                    return False
            window.evaluate_js('1')
            return True
        except Exception:
            return False

    def disable_json_editor(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.disableJsonEditor && window.disableJsonEditor()')
            except Exception as e:
                logger.error(f'disable_json_editor 执行失败: {e}')

    def enable_json_editor(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.enableJsonEditor && window.enableJsonEditor()')
            except Exception as e:
                logger.error(f'enable_json_editor 执行失败: {e}')

    def save_json_file(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.saveFile && window.saveFile()')
            except Exception as e:
                logger.error(f'save_json_file 执行失败: {e}')

    def toggle_screencast_fullscreen(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.toggleScreencastFullscreen && window.toggleScreencastFullscreen()')
            except Exception as e:
                logger.error(f'toggle_screencast_fullscreen 执行失败: {e}')

    def _notify_input_state(self, shown: bool, just_hidden: bool):
        try:
            if self._is_window_valid():
                js = f"window.__onInputState && window.__onInputState({str(shown).lower()},{str(just_hidden).lower()})"
                self._window.evaluate_js(js)
        except Exception:
            pass

    def notify_camera_mode_change(self, active, data):
        if not self._is_window_valid():
            return
        try:
            if active and data:
                js_code = (
                    'window.setCameraMode(true, '
                    f'{{"x": {data["center"][0]}, "y": {data["center"][1]}, "sensitivity": {data["sensitivity"]}}})'
                )
            else:
                js_code = 'window.setCameraMode(false)'
            self._window.evaluate_js(js_code)
        except Exception:
            pass

    def poll_input(self):
        """Poll input from frontend and send to device."""
        if not self._is_window_valid():
            return
        try:
            js = "document.getElementById('ime-input')?.value || ''"
            cur = self._window.evaluate_js(js)
            if cur:
                self._scrcpy_manager.send_text(''.join(cur))
                self._window.evaluate_js("window.__clearImeInput?.()")
        except Exception:
            pass
