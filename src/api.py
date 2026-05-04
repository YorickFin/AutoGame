import webview


class Api:
    def __init__(self):
        self._window = None
        self._maximized = False

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

    def __dir__(self):
        return ['get_app_info', 'minimize', 'close', 'toggle_maximize']
