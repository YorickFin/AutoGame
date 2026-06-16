import logging
import math
import subprocess
import sys

from ..services import services


logger = logging.getLogger(__name__)


class BackendApi:
    def __init__(self):
        self._no_key_names = ['MLeft', 'MRight', 'Middle', 'MSide1', 'MSide2']
        self._maximized = False

    @property
    def _macro(self):
        return services.macro

    @property
    def _utils_file(self):
        return services.utils_file

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    @property
    def _key_mapping(self):
        return services.key_mapping

    def get_config_file(self):
        config = self._utils_file.load_config_file()
        self._macro.set_macro_switch_key(config['macroSwitch'])
        return config

    def save_config_file(self, config):
        self._macro.set_macro_switch_key(config['macroSwitch'])
        return self._utils_file.save_config_file(config)

    def get_phone_input_state(self):
        km = self._key_mapping
        return {
            "keyboard_shown": km.keyboard_shown if km else None,
            "just_hidden": km.read_and_clear_just_hidden() if km else False,
        }

    def get_macro_files(self):
        return self._utils_file.get_macro_files()

    def load_macrofile(self, file_name: str):
        return self._utils_file.load_macro_file(file_name)

    def save_macrofile(self, file_name: str, macro_file: str):
        return self._utils_file.save_macro_file(file_name, macro_file)

    def create_new_file(self):
        return self._utils_file.create_new_file()

    def rename_file(self, old_name: str, new_name: str):
        return self._utils_file.rename_file(old_name, new_name)

    def open_folder(self, file_name: str):
        return self._utils_file.open_folder(file_name)

    def delete_file(self, file_name: str):
        return self._utils_file.delete_file(file_name)

    def clear_memory_logs(self):
        return self._utils_file.clear_memory_logs()

    def has_new_error(self):
        return self._utils_file.has_new_error()

    def clear_new_error_flag(self):
        return self._utils_file.clear_new_error_flag()

    def get_macro_switch_key_name(self):
        key_name = self._macro.get_key_name()
        if key_name in self._no_key_names:
            return False
        return key_name

    def get_key_name(self):
        return self._macro.get_key_name()

    def start_key_listener(self):
        self._macro.start_listening_key()
        return {"ok": True}

    def stop_key_listener(self):
        self._macro.stop_listening_key()
        return {"ok": True}

    def get_pressed_key(self):
        key = self._macro.get_last_key()
        return {"key": key}

    def set_focus_state(self, focused):
        if self._key_mapping:
            self._key_mapping.set_focus_state(focused)
        return {"ok": True}

    def get_mouse_position(self):
        x, y = self._macro.get_mouse_position()
        return f'{x}, {y}'

    def get_pixel_color(self):
        return self._macro.get_pixel_color()

    def get_memory_logs(self):
        return self._utils_file.get_memory_logs()

    def get_memory_logs_count(self):
        return self._utils_file.get_memory_logs_count()

    def get_memory_logs_since(self, index):
        return self._utils_file.get_memory_logs_since(index)

    def get_app_info(self):
        return self._utils_file._load_project_info()

    def minimize(self):
        logger.info('Minimize called')
        if self._window:
            try:
                self._window.minimize()
                logger.info('Window minimized successfully')
            except Exception as e:
                logger.error(f'Failed to minimize window: {e}')

    def close(self):
        logger.info('Close called')
        if self._window:
            try:
                config = self._utils_file.load_config_file()
                minimize_to_tray = config.get('minimizeToTray', True)
                if minimize_to_tray:
                    logger.info('Hiding window to tray')
                    self._window.hide()
                else:
                    logger.info('Destroying window')
                    self._window.destroy()
            except Exception as e:
                logger.error(f'Failed to close window: {e}')

    def toggle_maximize(self):
        logger.info('Toggle maximize called')
        if self._window:
            try:
                if self._maximized:
                    self._window.restore()
                    self._maximized = False
                    logger.info('Window restored')
                    return False
                self._window.maximize()
                self._maximized = True
                logger.info('Window maximized')
                return True
            except Exception as e:
                logger.error(f'Failed to toggle maximize: {e}')
        return False

    def get_screencast_ratio(self):
        width, height = self._macro.get_screen_size()
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
            logger.error(f'打开链接失败: {e}')
            return False

    def scrcpy_start(self, serial=None, config=None):
        return self._scrcpy_manager.start(serial, config)

    def scrcpy_stop(self):
        return self._scrcpy_manager.stop()

    def scrcpy_status(self):
        return self._scrcpy_manager.status()

    def scrcpy_get_ws_port(self):
        return self._scrcpy_manager.get_ws_port()

    def scrcpy_send_touch(self, action, x, y, width, height):
        return self._scrcpy_manager.send_touch(action, x, y, width, height)

    def scrcpy_send_keycode(self, keycode, action=0):
        return self._scrcpy_manager.send_keycode(keycode, action)

    def scrcpy_set_clipboard(self, text):
        return self._scrcpy_manager.set_clipboard(text)

    def scrcpy_send_text(self, text: str):
        logger.info(f"Sending text: {text}")
        return self._scrcpy_manager.send_text(text)

    def scrcpy_switch_to_wireless(self):
        return self._scrcpy_manager.switch_to_wireless()

    def scrcpy_discover_usb_serial(self):
        return self._scrcpy_manager.discover_usb_serial()

    def scrcpy_volume_up(self):
        return self._scrcpy_manager.volume_up()

    def scrcpy_volume_down(self):
        return self._scrcpy_manager.volume_down()

    def scrcpy_back(self):
        return self._scrcpy_manager.back()

    def scrcpy_switch_app(self):
        return self._scrcpy_manager.switch_app()

    def scrcpy_home(self):
        return self._scrcpy_manager.home()

    def get_key_mapping_files(self):
        return self._utils_file.get_key_mapping_files()

    def load_key_mapping_file(self, file_name):
        return self._utils_file.load_key_mapping_file(file_name)

    def save_key_mapping_file(self, file_name, data):
        return self._utils_file.save_key_mapping_file(file_name, data)

    def create_key_mapping_file(self):
        return self._utils_file.create_key_mapping_file()

    def rename_key_mapping_file(self, old_name, new_name):
        return self._utils_file.rename_key_mapping_file(old_name, new_name)

    def delete_key_mapping_file(self, file_name):
        return self._utils_file.delete_key_mapping_file(file_name)

    def apply_key_mapping(self, file_name):
        data = self._utils_file.load_key_mapping_file(file_name)
        if not data:
            return {"ok": False, "error": "failed to load key mapping"}
        self._scrcpy_manager.apply_key_mapping(data)
        if self._key_mapping:
            self._key_mapping.apply(data)
        return {"ok": True}

    def remove_key_mapping(self):
        self._scrcpy_manager.remove_key_mapping()
        if self._key_mapping:
            self._key_mapping.remove()
        return {"ok": True}

    def scrcpy_send_normalized_touch(self, action, x, y):
        return self._scrcpy_manager.send_normalized_touch(action, x, y)

    def get_key_mapping_mapped_keys(self):
        if self._key_mapping:
            return list(self._key_mapping.get_mapped_keys())
        return []

    def key_mapping_trigger(self, key_name, action):
        return self._scrcpy_manager.key_mapping_trigger(key_name, action)

    def key_mapping_swipe(self, path_data):
        return self._scrcpy_manager.key_mapping_swipe(path_data)

    def get_android_keycode(self, key_name):
        return self._scrcpy_manager.key_mapping_get_android_keycode(key_name)

    def set_screencast_ratio(self, ratio):
        if ratio == "reset":
            return self._scrcpy_manager.reset_screen_ratio()
        if ratio == "monitor":
            w, h = self._macro.get_screen_size()
            w, h = int(w), int(h)
            gcd = math.gcd(w, h)
            wr, hr = w // gcd, h // gcd
            return self._scrcpy_manager.set_screen_ratio(wr, hr)
        if ratio == "16:9":
            return self._scrcpy_manager.set_screen_ratio(16, 9)
        return {"ok": False, "error": f"unknown ratio: {ratio}"}

    def has_mleft_key_configured(self):
        if self._key_mapping:
            return self._key_mapping.has_mleft_key_configured()
        return False

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
            'get_key_mapping_mapped_keys',
            'start_key_listener',
            'set_focus_state',
            'stop_key_listener',
            'get_pressed_key',
            'get_phone_input_state',
            'has_mleft_key_configured',
        ]
