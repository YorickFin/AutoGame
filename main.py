# 打包为exe文件: pyinstaller main.spec -y

import logging
import webview
import pystray
import subprocess
from threading import Thread
from PIL import Image
from src.api import Api
from src.services import services
from src.utils import WebView2Checker, UtilsFile, UtilsUpdate, utils_path, ocr
from src.macro import Macro
from src.key_mapping import KeyMapping
from src.scrcpy import ScrcpyManager, WsStreamServer


logger = logging.getLogger(__name__)


class AutoGameApp:
    def __init__(self):
        services.utils_path = utils_path
        services.ocr = ocr
        services.utils_file = UtilsFile()
        services.ws_stream_server = WsStreamServer()
        services.scrcpy_manager = ScrcpyManager()
        services.api = Api()
        services.macro = Macro()
        services.key_mapping = KeyMapping()

        self.webview2_checker = WebView2Checker()

        # 初始化更新模块：提取内嵌的 update.exe / update.json
        self.utils_update = UtilsUpdate()
        self.utils_update.extract_bundled_files()

        self.debug = True
        self.window = None
        self.tray = None

    @property
    def _utils_path(self):
        return services.utils_path

    @property
    def _api(self):
        return services.api

    @property
    def _macro(self):
        return services.macro

    def _get_adaptive_window_size(self):
        """
        获取自适应窗口大小，根据屏幕分辨率调整。
        """
        screen_width, screen_height = self._macro.get_screen_size()

        scale_factor = (screen_width - 1920) * (0.2 / 640)
        scale_w = 1.8 + scale_factor
        scale_h = 1.6 + scale_factor

        win_width = int(screen_width / scale_w)
        win_height = int(screen_height / scale_h)

        pos_x = int((screen_width / 2) - (win_width / 2))
        pos_y = int((screen_height / 2) - (win_height / 1.7))

        return win_width, win_height, pos_x, pos_y

    def _get_index_path(self):
        """
        获取HTML文件的路径，先检查打包环境的路径，若不存在则返回开发环境的路径。
        """
        # 检查打包环境的路径
        if self._utils_path.is_frozen():
            index_path = self._utils_path.index_html_path
            if index_path.exists():
                self.debug = False
                return str(index_path)
        # 开发环境
        self.debug = True
        return 'http://localhost:5173'

    def _create_window(self):
        """
        创建主窗口。
        """
        win_width, win_height, pos_x, pos_y = self._get_adaptive_window_size()
        index_path = self._get_index_path()

        self.window = webview.create_window(
            title='AutoGame',
            url=index_path,
            width=win_width,
            height=win_height,
            x=pos_x,
            y=pos_y,
            frameless=True,
            easy_drag=False,
            js_api=self._api
        )
        services.window = self.window
        self.window.events.closed += self.on_window_closed

    def on_window_closed(self):
        """
        窗口关闭事件处理。
        """
        if self.tray:
            self.tray.visible = False
            self.tray.stop()
        if self._macro:
            self._macro.restore_mouse_icon()
            self._macro.stop()
        logger.info('应用已关闭')

    def show_window(self):
        """
        显示主窗口。
        """
        if self.window:
            self.window.show()

    def exit_app(self):
        """
        退出应用。
        """
        if self.window:
            self.window.destroy()
        if self.tray:
            self.tray.visible = False
            self.tray.stop()
        if self._macro:
            self._macro.restore_mouse_icon()
            self._macro.stop()
        subprocess.Popen(
            "taskkill /f /im adb.exe",
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # 退出时触发更新解压覆盖
        if hasattr(self, 'utils_update'):
            self.utils_update.apply_on_exit()

    def _create_tray(self):
        """
        创建系统托盘图标。
        """
        icon_path = self._utils_path.logo_tray_path
        image = Image.open(icon_path)

        def on_tray_click(icon, item):
            self.show_window()

        menu = pystray.Menu(
            pystray.MenuItem('显示主界面', on_tray_click, default=True),
            pystray.MenuItem('退出', self.exit_app)
        )

        self.tray = pystray.Icon('AutoGame', image, 'AutoGame', menu)

    def run_tray(self):
        """
        运行系统托盘图标。
        """
        self._create_tray()
        self.tray.run()

    def run(self):
        """
        运行应用。
        """
        self._create_window()
        Thread(target=self.run_tray).start()
        Thread(target=self._macro.start).start()

        # 后台线程检查版本更新
        self.utils_update.start_update_check()

        webview.start(debug=self.debug)


if __name__ == '__main__':
    app = AutoGameApp()
    app.webview2_checker.check_and_prompt()
    app.run()
