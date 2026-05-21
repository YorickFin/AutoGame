

import subprocess
import sys
import math
from .scrcpy_manager import ScrcpyManager
from .key_mapping_executor import KeyMappingExecutor

class Api:
    def __init__(self, logger, macro, file_manager):
        self.logger = logger
        self.macro = macro
        self.file_manager = file_manager
        self._no_key_names = ['MLeft', 'MRight', 'Middle', 'MSide1', 'MSide2']

        self._window = None
        self._maximized = False
        self.scrcpy = ScrcpyManager()
        self.key_mapping_executor = KeyMappingExecutor(self.scrcpy)

    def get_config_file(self):
        config = self.file_manager.load_config_file()
        self.macro.set_macro_switch_key(config['macroSwitch'])
        return config

    def save_config_file(self, config):
        self.macro.set_macro_switch_key(config['macroSwitch'])
        return self.file_manager.save_config_file(config)

    def get_macro_files(self):
        return self.file_manager.get_macro_files()

    def load_macrofile(self, file_name: str):
        return self.file_manager.load_macro_file(file_name)

    def save_macrofile(self, file_name: str, macro_file: str):
        return self.file_manager.save_macro_file(file_name, macro_file)

    def create_new_file(self):
        return self.file_manager.create_new_file()

    def rename_file(self, old_name: str, new_name: str):
        return self.file_manager.rename_file(old_name, new_name)

    def open_folder(self, file_name: str):
        return self.file_manager.open_folder(file_name)

    def delete_file(self, file_name: str):
        return self.file_manager.delete_file(file_name)

    def clear_memory_logs(self):
        return self.file_manager.clear_memory_logs()

    def has_new_error(self):
        return self.file_manager.has_new_error()

    def clear_new_error_flag(self):
        return self.file_manager.clear_new_error_flag()

    def get_macro_switch_key_name(self):
        key_name = self.macro.get_key_name()
        if key_name in self._no_key_names:
            return False
        return key_name

    def get_key_name(self):
        key_name = self.macro.get_key_name()
        return key_name

    def start_key_listener(self):
        """开始监听按键输入，用于前端轮询获取按键名称"""
        self.macro.start_listening_key()
        return {"ok": True}

    def stop_key_listener(self):
        """停止监听按键输入"""
        self.macro.stop_listening_key()
        return {"ok": True}

    def get_pressed_key(self):
        """获取最后按下的按键，用于前端轮询"""
        key = self.macro.get_last_key()
        return {"key": key}

    def set_focus_state(self, focused):
        if self.key_mapping_executor:
            self.key_mapping_executor.set_focus_state(focused)
        return {"ok": True}

    def get_mouse_position(self):
        x, y = self.macro.get_mouse_position()
        return f'{x}, {y}'

    def get_pixel_color(self):
        color = self.macro.get_pixel_color()
        return color

    def get_memory_logs(self):
        return self.file_manager.get_memory_logs()

    def get_memory_logs_count(self):
        return self.file_manager.get_memory_logs_count()

    def get_memory_logs_since(self, index):
        return self.file_manager.get_memory_logs_since(index)

    def set_window(self, window):
        self._window = window

    def get_app_info(self):
        return self.file_manager._load_project_info()

    def minimize(self):
        self.logger.info('Minimize called')
        if self._window:
            try:
                self._window.minimize()
                self.logger.info('Window minimized successfully')
            except Exception as e:
                self.logger.error(f'Failed to minimize window: {e}')

    def close(self):
        self.logger.info('Close called')
        if self._window:
            try:
                config = self.file_manager.load_config_file()
                minimize_to_tray = config.get('minimizeToTray', True)
                if minimize_to_tray:
                    self.logger.info('Hiding window to tray')
                    self._window.hide()
                else:
                    self.logger.info('Destroying window')
                    self._window.destroy()
            except Exception as e:
                self.logger.error(f'Failed to close window: {e}')

    def toggle_maximize(self):
        self.logger.info('Toggle maximize called')
        if self._window:
            try:
                if self._maximized:
                    self._window.restore()
                    self._maximized = False
                    self.logger.info('Window restored')
                    return False
                else:
                    self._window.maximize()
                    self._maximized = True
                    self.logger.info('Window maximized')
                    return True
            except Exception as e:
                self.logger.error(f'Failed to toggle maximize: {e}')
        return False

    def get_screencast_ratio(self):
        width, height = self.macro.get_screen_size()
        width, height = int(width), int(height)
        gcd = math.gcd(width, height)
        width_ratio = width // gcd
        height_ratio = height // gcd
        return f'{width_ratio}:{height_ratio}'

    def open_url(self, url: str):
        try:
            if sys.platform == 'win32':
                subprocess.run(['start', url], shell=True)
            elif sys.platform == 'darwin':
                subprocess.run(['open', url])
            else:
                subprocess.run(['xdg-open', url])
            return True
        except Exception as e:
            self.logger.error(f'打开链接失败: {e}')
            return False

    def _is_window_valid(self):
        """检查窗口是否仍然有效且可访问"""
        if not self._window:
            return False
        try:
            if hasattr(self._window, '_impl') and hasattr(self._window._impl, 'webview'):
                import ctypes
                if ctypes.c_long(self._window._impl.webview.IsDisposed).value != 0:
                    return False
            self._window.evaluate_js('1')
            return True
        except Exception:
            return False

    def disable_json_editor(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.disableJsonEditor && window.disableJsonEditor()')
            except Exception as e:
                self.logger.error(f'disable_json_editor 执行失败: {e}')

    def enable_json_editor(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.enableJsonEditor && window.enableJsonEditor()')
            except Exception as e:
                self.logger.error(f'enable_json_editor 执行失败: {e}')

    def save_json_file(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.saveFile && window.saveFile()')
            except Exception as e:
                self.logger.error(f'save_json_file 执行失败: {e}')

    def toggle_screencast_fullscreen(self):
        if self._is_window_valid():
            try:
                self._window.evaluate_js('window.toggleScreencastFullscreen && window.toggleScreencastFullscreen()')
            except Exception as e:
                self.logger.error(f'toggle_screencast_fullscreen 执行失败: {e}')


    # ------------------------------------------------------------------ #
    # Scrcpy / screencast API
    # ------------------------------------------------------------------ #

    def scrcpy_start(self, serial=None, config=None):
        return self.scrcpy.start(serial, config)

    def scrcpy_stop(self):
        return self.scrcpy.stop()

    def scrcpy_status(self):
        return self.scrcpy.status()

    def scrcpy_get_ws_port(self):
        return self.scrcpy.get_ws_port()

    def scrcpy_send_touch(self, action, x, y, width, height):
        return self.scrcpy.send_touch(action, x, y, width, height)

    def scrcpy_send_keycode(self, keycode, action=0):
        return self.scrcpy.send_keycode(keycode, action)

    def scrcpy_set_clipboard(self, text):
        return self.scrcpy.set_clipboard(text)

    def scrcpy_switch_to_wireless(self):
        return self.scrcpy.switch_to_wireless()

    def scrcpy_discover_usb_serial(self):
        return self.scrcpy.discover_usb_serial()

    def scrcpy_volume_up(self):
        return self.scrcpy.volume_up()

    def scrcpy_volume_down(self):
        return self.scrcpy.volume_down()

    def scrcpy_back(self):
        return self.scrcpy.back()

    def scrcpy_switch_app(self):
        return self.scrcpy.switch_app()

    def scrcpy_home(self):
        return self.scrcpy.home()



    # ------------------------------------------------------------------ #
    # Key mapping API
    # ------------------------------------------------------------------ #

    def get_key_mapping_files(self):
        return self.file_manager.get_key_mapping_files()

    def load_key_mapping_file(self, file_name):
        return self.file_manager.load_key_mapping_file(file_name)

    def save_key_mapping_file(self, file_name, data):
        return self.file_manager.save_key_mapping_file(file_name, data)

    def create_key_mapping_file(self):
        return self.file_manager.create_key_mapping_file()

    def rename_key_mapping_file(self, old_name, new_name):
        return self.file_manager.rename_key_mapping_file(old_name, new_name)

    def delete_key_mapping_file(self, file_name):
        return self.file_manager.delete_key_mapping_file(file_name)

    def set_key_mapping_executor(self, executor):
        self.key_mapping_executor = executor
        if self.macro:
            self.macro.set_key_mapping_executor(executor)
        return {"ok": True}

    def apply_key_mapping(self, file_name):
        data = self.file_manager.load_key_mapping_file(file_name)
        if not data:
            return {"ok": False, "error": "failed to load key mapping"}
        self.scrcpy.apply_key_mapping(data)
        self.key_mapping_executor.apply(data)
        return {"ok": True}

    def remove_key_mapping(self):
        self.scrcpy.remove_key_mapping()
        self.key_mapping_executor.remove()
        return {"ok": True}

    def scrcpy_send_normalized_touch(self, action, x, y):
        return self.scrcpy.send_normalized_touch(action, x, y)

    def get_key_mapping_mapped_keys(self):
        if hasattr(self, 'key_mapping_executor') and self.key_mapping_executor:
            return list(self.key_mapping_executor.get_mapped_keys())
        return []

    def key_mapping_trigger(self, key_name, action):
        return self.scrcpy.key_mapping_trigger(key_name, action)

    def key_mapping_swipe(self, path_data):
        return self.scrcpy.key_mapping_swipe(path_data)

    def get_android_keycode(self, key_name):
        return self.scrcpy.key_mapping_get_android_keycode(key_name)

    def set_screencast_ratio(self, ratio):
        if ratio == "reset":
            return self.scrcpy.reset_screen_ratio()
        elif ratio == "monitor":
            w, h = self.macro.get_screen_size()
            w, h = int(w), int(h)
            gcd = math.gcd(w, h)
            wr, hr = w // gcd, h // gcd
            return self.scrcpy.set_screen_ratio(wr, hr)
        elif ratio == "16:9":
            return self.scrcpy.set_screen_ratio(16, 9)
        else:
            return {"ok": False, "error": f"unknown ratio: {ratio}"}


    def __dir__(self):
        return [
            'get_app_info', 'minimize', 'close', 'toggle_maximize', 'get_screencast_ratio', 'open_url',
            'get_config_file', 'save_config_file',
            'get_macro_switch_key_name', 'get_key_name', 'get_mouse_position', 'get_pixel_color',
            'get_macro_files', 'load_macrofile', 'save_macrofile',
            'create_new_file', 'rename_file', 'open_folder', 'delete_file',
            'get_memory_logs', 'get_memory_logs_count', 'get_memory_logs_since', 'clear_memory_logs', 'has_new_error', 'clear_new_error_flag',
            'disable_json_editor', 'enable_json_editor', 'save_json_file',
            'set_screencast_ratio',
            'toggle_screencast_fullscreen',
            'scrcpy_start', 'scrcpy_stop', 'scrcpy_status', 'scrcpy_get_ws_port', 'scrcpy_send_touch', 'scrcpy_send_keycode', 'scrcpy_set_clipboard',
            'scrcpy_switch_to_wireless', 'scrcpy_discover_usb_serial',
            'scrcpy_volume_up', 'scrcpy_volume_down', 'scrcpy_back',
            'scrcpy_switch_app', 'scrcpy_home',
            'get_key_mapping_files',
            'load_key_mapping_file',
            'save_key_mapping_file',
            'create_key_mapping_file',
            'rename_key_mapping_file',
            'delete_key_mapping_file',
            'apply_key_mapping',
            'remove_key_mapping',
            'key_mapping_trigger',
            'key_mapping_swipe',
            'get_android_keycode',
            'scrcpy_send_normalized_touch',
            'set_key_mapping_executor',
            'get_key_mapping_mapped_keys',
            'start_key_listener',
            'set_focus_state',
            'stop_key_listener',
            'get_pressed_key',
        ]



