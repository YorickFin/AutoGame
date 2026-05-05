
import os
import json


class Api:
    def __init__(self):
        self._window = None
        self._maximized = False
        self._config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'config', 'config.json')
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        config_dir = os.path.dirname(self._config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

    def _load_config(self):
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_config(self, config):
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    def set_window(self, window):
        self._window = window

    def get_app_info(self):
        return {
            'name': 'AutoGame',
            'version': '0.1.0'
        }

    def minimize(self):
        if self._window:
            self._window.minimize()

    def close(self):
        if self._window:
            self._window.destroy()

    def toggle_maximize(self):
        if self._window:
            if self._maximized:
                self._window.restore()
                self._maximized = False
                return False
            else:
                self._window.maximize()
                self._maximized = True
                return True
        return False

    def get_config(self):
        return self._load_config()

    def save_config(self, config):
        return self._save_config(config)

    def __dir__(self):
        return ['get_app_info', 'minimize', 'close', 'toggle_maximize', 'get_config', 'save_config']
