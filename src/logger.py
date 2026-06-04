import logging
from datetime import datetime
from .utils.utils_path import utils_path

class MemoryLogHandler(logging.Handler):
    """内存日志处理器，将日志存储在内存中并提供错误检测功能"""

    def __init__(self):
        """初始化内存日志处理器"""
        super().__init__()
        self.logs = []
        self.max_logs = 1000
        self._has_new_error = False

    def emit(self, record):
        """
        处理日志记录

        Args:
            record: 日志记录对象
        """
        try:
            msg = self.format(record)
            self.logs.append(msg)
            if record.levelno >= logging.ERROR:
                self._has_new_error = True
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
        except Exception:
            self.handleError(record)

    def get_logs(self):
        """
        获取所有日志

        Returns:
            str: 用换行符连接的所有日志
        """
        return '\n'.join(self.logs)

    def get_logs_count(self):
        """
        获取日志条目数量

        Returns:
            int: 日志条目总数
        """
        return len(self.logs)

    def get_logs_since(self, index):
        """
        获取从指定索引开始的增量日志

        Args:
            index: 起始索引位置

        Returns:
            dict: 包含日志内容和新索引位置的字典
        """
        if index >= len(self.logs):
            return {'content': '', 'new_index': len(self.logs)}
        return {
            'content': '\n'.join(self.logs[index:]),
            'new_index': len(self.logs)
        }

    def clear_logs(self):
        """清空所有日志并重置错误标志"""
        self.logs = []
        self._has_new_error = False

    def has_new_error(self):
        """
        检查是否有新的错误日志

        Returns:
            bool: 是否有新错误
        """
        return self._has_new_error

    def clear_new_error_flag(self):
        """清除新错误标志"""
        self._has_new_error = False


class Logger:
    """日志管理类，负责配置和管理日志系统"""

    def __init__(self):
        """初始化日志管理器"""
        self._memory_handler = MemoryLogHandler()

    def setup_logging(self, utils_path):
        """
        配置日志系统

        Args:
            utils_path: 路径管理器对象，需包含 logs_dir 属性

        Returns:
            logging.Logger: 配置好的日志记录器
        """
        date_format = '%Y_%m_%d__%H_%M_%S'
        log_format = '%(asctime)s - %(levelname)s - %(message)s'

        path = utils_path.logs_dir

        log_files = list(path.glob('*.log'))
        if len(log_files) > 4:
            log_files.sort(key=lambda x: x.stat().st_mtime)
            for log_file in log_files[:-4]:
                log_file.unlink()

        log_filename = path / f'{datetime.now().strftime(date_format)}.log'

        self._memory_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler(),
                self._memory_handler
            ]
        )

        return logging.getLogger(__name__)

    def get_memory_handler(self):
        """
        获取内存日志处理器

        Returns:
            MemoryLogHandler: 内存日志处理器实例
        """
        return self._memory_handler


# 全局日志记录器实例 （单例模式）
logger_manager = Logger()
logger = logger_manager.setup_logging(utils_path)
