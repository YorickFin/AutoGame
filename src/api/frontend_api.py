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
        """
        Desc:
            检查前端窗口是否有效可用
        Returns:
            bool: 窗口有效返回 True，否则返回 False
        """
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
        """
        Desc:
            禁用前端的 JSON 编辑器
        """
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.disableJsonEditor && window.disableJsonEditor()')
            except Exception as e:
                logger.error(f'disable_json_editor 执行失败: {e}')

    def enable_json_editor(self):
        """
        Desc:
            启用前端的 JSON 编辑器
        """
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.enableJsonEditor && window.enableJsonEditor()')
            except Exception as e:
                logger.error(f'enable_json_editor 执行失败: {e}')

    def save_json_file(self):
        """
        Desc:
            触发前端保存 JSON 文件操作
        """
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.saveFile && window.saveFile()')
            except Exception as e:
                logger.error(f'save_json_file 执行失败: {e}')

    def toggle_screencast_fullscreen(self):
        """
        Desc:
            切换投屏全屏/窗口模式
        """
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.toggleScreencastFullscreen && window.toggleScreencastFullscreen()')
            except Exception as e:
                logger.error(f'toggle_screencast_fullscreen 执行失败: {e}')

    def _notify_input_state(self, shown: bool, just_hidden: bool):
        """
        Desc:
            通知前端输入状态变化
        Args:
            shown (bool): 键盘是否显示
            just_hidden (bool): 是否刚隐藏键盘
        """
        try:
            if self._is_window_valid():
                js = f"window.__onInputState && window.__onInputState({str(shown).lower()},{str(just_hidden).lower()})"
                self._window.evaluate_js(js)
        except Exception:
            pass

    def notify_camera_mode_change(self, active, data):
        """
        Desc:
            通知前端摄像头模式变化
        Args:
            active (bool): 是否启用摄像头模式
            data (dict or None): 摄像头数据，包含 center 和 sensitivity 字段
        """
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
        """
        Desc:
            从前端轮询输入内容并发送到设备
        """
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
