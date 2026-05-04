import webview
import os
import sys
import ctypes
from src.api import Api


class AutoGameApp:
    def __init__(self):
        self.is_frozen = getattr(sys, 'frozen', False)
        self.debug = not self.is_frozen
        self.api = Api()
        self.window = None

    def get_adaptive_window_size(self):
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)

        scale_factor = (screen_width - 1920) * (0.2 / 640)
        scale_w = 1.8 + scale_factor
        scale_h = 1.6 + scale_factor

        win_width = int(screen_width / scale_w)
        win_height = int(screen_height / scale_h)

        pos_x = int((screen_width / 2) - (win_width / 2))
        pos_y = int((screen_height / 2) - (win_height / 1.7))

        return win_width, win_height, pos_x, pos_y

    def _get_index_path(self):
        if self.is_frozen:
            frontend_path = os.path.join(sys._MEIPASS, 'frontend', 'dist')
            return os.path.join(frontend_path, 'index.html')
        return 'http://localhost:5173'

    def _create_window(self):
        win_width, win_height, pos_x, pos_y = self.get_adaptive_window_size()
        index_path = self._get_index_path()

        self.window = webview.create_window(
            title='AutoGame',
            url=index_path,
            width=win_width,
            height=win_height,
            x=pos_x,
            y=pos_y,
            frameless=True,
            easy_drag=True,
            js_api=self.api
        )
        self.api.set_window(self.window)

    def run(self):
        self._create_window()
        webview.start(debug=self.debug)


if __name__ == '__main__':
    app = AutoGameApp()
    app.run()
