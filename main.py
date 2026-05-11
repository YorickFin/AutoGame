import webview
import sys
import logging
from pathlib import Path
from datetime import datetime
from threading import Thread
from PIL import Image
import pystray
from src.api import Api
from src.ocr import ocr
from src.macro import Macro
from src.file_manager import FileManager

# 自定义日志Handler，用于捕获日志到内存
class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []
        self.max_logs = 1000  # 最多保存1000条日志
        self._has_new_error = False

    def emit(self, record):
        try:
            msg = self.format(record)
            self.logs.append(msg)
            # 检测是否是 error 或更高级别的日志
            if record.levelno >= logging.ERROR:
                self._has_new_error = True
            # 限制日志数量
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
        except Exception:
            self.handleError(record)

    def get_logs(self):
        return '\n'.join(self.logs)

    def clear_logs(self):
        self.logs = []
        self._has_new_error = False

    def has_new_error(self):
        """检查是否有新的错误
        Returns:
            bool: 是否有未读的错误
        """
        return self._has_new_error

    def clear_new_error_flag(self):
        """清除新错误的标记
        """
        self._has_new_error = False

# 全局内存日志Handler实例
memory_handler = MemoryLogHandler()


def setup_logging():
    """
    配置日志系统
    """
    # 配置日志
    date_format = '%Y_%m_%d__%H_%M_%S'
    log_format = '%(asctime)s - %(levelname)s - %(message)s'

    # 创建logs目录
    path = Path('logging')
    path.mkdir(parents=True, exist_ok=True)

    # 只保留最近的5个日志文件
    for log_file in path.glob('*.log'):
        if len(list(path.glob('*.log'))) > 4:
            log_file.unlink()

    # 设置日志文件名
    log_filename = path / f'{datetime.now().strftime(date_format)}.log'

    # 配置内存handler的格式
    memory_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # 配置日志系统
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(),
            memory_handler
        ]
    )

    return logging.getLogger(__name__)


class AutoGameApp:
    def __init__(self):
        self.logger = setup_logging()
        self.macro = Macro(self.logger, ocr)
        self.file_manager = FileManager(self.logger, self.macro)
        self.file_manager.set_memory_handler(memory_handler)
        self.api = Api(self.logger, self.file_manager, self.macro)

        self.is_frozen = getattr(sys, 'frozen', False)
        self.debug = not self.is_frozen
        self.window = None
        self.tray = None

    def get_adaptive_window_size(self):
        screen_width, screen_height = self.macro.get_screen_size()

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
            frontend_path = Path(sys._MEIPASS) / 'frontend' / 'dist'
            return frontend_path / 'index.html'
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
            easy_drag=False,
            js_api=self.api
        )
        self.api.set_window(self.window)
        self.window.events.closed += self.on_window_closed

    def on_window_closed(self):
        if self.tray:
            self.tray.visible = False
            self.tray.stop()

    def show_window(self):
        if self.window:
            self.window.show()

    def exit_app(self):
        if self.window:
            self.window.destroy()
        if self.tray:
            self.tray.visible = False
            self.tray.stop()
        if self.macro:
            self.macro.stop()

    def _create_tray(self):
        icon_path = r'data\logo\logo_tray.png'
        image = Image.open(icon_path)

        def on_tray_click(icon, item):
            self.show_window()

        menu = pystray.Menu(
            pystray.MenuItem('显示主界面', on_tray_click, default=True),
            pystray.MenuItem('退出', self.exit_app)
        )

        self.tray = pystray.Icon('AutoGame', image, 'AutoGame', menu)

    def run_tray(self):
        self._create_tray()
        self.tray.run()

    def run(self):
        self._create_window()
        Thread(target=self.run_tray, daemon=True).start()
        Thread(target=self.macro.start, daemon=True).start()
        webview.start(debug=self.debug)


if __name__ == '__main__':
    app = AutoGameApp()
    app.run()
