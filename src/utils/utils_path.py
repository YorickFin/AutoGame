import sys
from pathlib import Path


class UtilsPath:
    """统一路径管理类，处理开发环境和打包环境的路径问题"""

    def __init__(self):
        """初始化路径管理器，计算各种基础路径"""
        if hasattr(self, '_initialized'):
            return

        # 获取基础路径
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller打包环境 - 资源路径（临时解压目录）
            self.base_res_path = Path(sys._MEIPASS)
            # 用户数据路径 - 使用exe所在目录
            self.base_user_path = Path(sys.executable).parent
        else:
            # 开发环境 - 资源在项目根目录
            self.base_res_path = Path(__file__).parent.parent.parent
            self.base_user_path = Path(__file__).parent.parent.parent

        # 确保用户数据目录存在
        self.base_user_path.mkdir(parents=True, exist_ok=True)

        self._initialized = True

    def get_resource_path(self, relative_path: str) -> Path:
        """
        获取资源文件的绝对路径
        Args:
            relative_path: 相对于资源根目录的相对路径
        Returns:
            资源文件的绝对路径
        """
        return self.base_res_path / relative_path

    def get_user_path(self, relative_path: str) -> Path:
        """
        获取用户数据文件的绝对路径
        Args:
            relative_path: 相对于用户数据根目录的相对路径
        Returns:
            用户数据文件的绝对路径
        """
        return self.base_user_path / relative_path

    def ensure_user_dir(self, relative_path: str) -> Path:
        """
        确保用户数据目录存在，如果不存在则创建
        Args:
            relative_path: 相对于用户数据根目录的相对路径
        Returns:
            用户数据目录的绝对路径
        """
        dir_path = self.get_user_path(relative_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @property
    def key_mapping_dir(self) -> Path:
        return self.ensure_user_dir(r"data\key_mapping")

    @property
    def config_path(self) -> Path:
        """配置文件路径"""
        return self.get_user_path(r'data\config\config.json')

    @property
    def macro_dir(self) -> Path:
        """宏文件目录"""
        return self.ensure_user_dir(r'data\macrofile')

    @property
    def target_image_dir(self) -> Path:
        """目标图像目录"""
        return self.ensure_user_dir(r'data\target_image')

    @property
    def logs_dir(self) -> Path:
        """日志目录"""
        return self.ensure_user_dir('logging')

    @property
    def pyproject_path(self) -> Path:
        """pyproject.toml文件路径"""
        return self.get_resource_path('pyproject.toml')

    @property
    def logo_tray_path(self) -> Path:
        """托盘图标路径"""
        return self.get_resource_path(r'data\logo\logo_tray.png')

    @property
    def cursor_path(self) -> Path:
        """鼠标光标路径"""
        return self.get_resource_path(r'data\config\CursorNormal.cur')

    @property
    def index_html_path(self) -> Path:
        """前端index.html路径（打包环境）"""
        return self.get_resource_path(r'frontend\dist\index.html')

    def is_frozen(self) -> bool:
        """
        判断是否为打包环境
        Returns:
            True表示打包环境，False表示开发环境
        """
        return getattr(sys, 'frozen', False)

# 全局路径管理器实例 （单例模式）
utils_path = UtilsPath()
