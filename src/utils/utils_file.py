import logging
import shutil
import json
import ast
import tomli
import subprocess

from ..services import services
from .utils_path import utils_path
from ..logger import logger_manager

logger = logging.getLogger(__name__)

class UtilsFile:

    def __init__(self):
        self._memory_handler = logger_manager.get_memory_handler()

        self.file_list = []

        self.config = {}
        self._init_config()

    @property
    def macro(self):
        return services.macro

    def _init_config(self):
        """初始化配置文件"""
        try:
            if not utils_path.config_path.exists():
                # 工作目录没有配置文件，从资源目录复制
                res_config_path = utils_path.base_res_path / 'data' / 'config' / 'config.json'
                utils_path.config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(res_config_path, utils_path.config_path)

                res_macrofile_dir = utils_path.base_res_path / 'data' / 'macrofile' / 'A示例文件.json'
                utils_path.macro_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(res_macrofile_dir, utils_path.macro_dir)

                target_image = utils_path.base_user_path / 'data' / 'target_image'
                target_image.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f'初始化配置文件失败: {e}')

    def _load_project_info(self):
        try:
            with open(utils_path.pyproject_path, 'rb') as f:
                data = tomli.load(f)
            return {
                'name': data['project']['name'],
                'version': data['project']['version'],
                'homepage': data['urls']['homepage'],
                'instructions': data['urls']['instructions']
            }
        except Exception as e:
            logger.error(f'加载项目信息 报错信息：{e}')
            return {'name': 'AutoGame', 'version': '0.0.0'}

    def load_config_file(self):
        """
            加载配置文件
        Returns:
            dict | False: 配置文件内容字典 | False
        """
        try:
            if utils_path.config_path.exists():
                with open(utils_path.config_path, 'r', encoding='utf-8-sig') as f:
                    self.config = json.load(f)
            else:
                utils_path.config_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f'加载配置文件 报错信息：{e}')
            return False
        finally:
            return self.config

    def save_config_file(self, config):
        """
            保存配置文件
        Args:
            config (dict): 配置文件内容字典
        Returns:
            bool: 是否成功保存
        """
        try:
            with open(utils_path.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f'保存配置文件 报错信息：{e}')
            return False

    def get_macro_files(self):
        """
            获取 dir 下的所有 json 文件
        Returns:
            list: 所有 json 文件名列表(不包含扩展名)
        """
        self.file_list = [f.stem for f in utils_path.macro_dir.glob('*.json') if f.suffix == '.json']
        logger.info(f'宏文件列表：{self.file_list}')
        return self.file_list

    def load_macro_file(self, file_name: str):
        """
            加载宏文件
        Args:
            file_name (str): 宏文件名(不包含扩展名)
        Returns:
            dict | False: 宏文件内容字典 | False
        """
        logger.info(f'加载宏文件：{file_name}')
        file_path = utils_path.macro_dir / f'{file_name}.json'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                macro_file = json.load(f)
            self.macro.set_macro_file(macro_file)
            return macro_file
        except Exception as e:
            logger.error(f'加载宏文件 报错信息：{e}')
            return False

    def save_macro_file(self, file_name: str, macro_file: str):
        """
            保存宏文件
        Args:
            file_name (str): 宏文件名(不包含扩展名)
            macro_file (str): 宏文件内容文字
        Returns:
            dict | False: 宏文件内容字典 | False
        """

        def preprocess_file(macro_file: str):
            """
                预处理宏文件
            Args:
                macro_file (str): 宏文件内容文字
            Returns:
                dict | False: 宏文件内容字典 | False
            """
            try:
                replacements = {
                    '：': ':',
                    '，': ',',
                    '， ': ',',
                    ', ': ',',
                    '‘': '"',
                    '’': '"',
                    "“": '"',
                    "”": '"',
                    "'": '"',
                    '！': '!',
                    '延时': '延迟'
                }
                text = macro_file
                for old, new in replacements.items():
                    text = text.replace(old, new)
                return ast.literal_eval(text)
            except Exception as e:
                logger.error(f'预处理宏文件 报错信息：{e}')
                return False

        def save_file(macro_file: dict, file_path: str):
            """
                保存宏文件
            Args:
                macro_file (dict): 宏文件内容字典
                file_path (str): 宏文件路径
            """
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(macro_file, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f'保存宏文件 报错信息：{e}')
                return False

        try:
            logger.info(f'保存宏文件：{file_name}')
            file_path = utils_path.macro_dir / f'{file_name}.json'
            macro_file = preprocess_file(macro_file)
            if not macro_file:
                return False
            save_file(macro_file, file_path)
            self.macro.set_macro_file(macro_file)
            return macro_file
        except Exception as e:
            logger.error(f'保存宏文件 报错信息：{e}')
            return False

    def create_new_file(self):
        """
            创建新文件
        """
        try:
            new_file_content = [
                {
                    '备注': '基本信息',
                    '按键更改': '',
                    '坐标更改': f'{self.macro.get_screen_size()}',
                    '窗口标题': '',
                    '窗口类名': '',
                    '鼠标图标更改': '是'
                }
            ]
            new_file_name = ''
            for i in range(1, 1000):
                if f'新建文件{i}' not in self.file_list:
                    new_file_name = f'新建文件{i}'
                    break
            logger.info(f'创建新文件：{new_file_name}')
            with open(utils_path.macro_dir / f'{new_file_name}.json', 'w', encoding='utf-8') as f:
                json.dump(new_file_content, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f'创建新文件 报错信息：{e}')
            return False

    def rename_file(self, old_name: str, new_name: str):
        """
            重命名文件
        Args:
            old_name (str): 旧文件名(不包含扩展名)
            new_name (str): 新文件名(不包含扩展名)
        """
        try:
            logger.info(f'重命名文件：{old_name} -> {new_name}')
            file_path = utils_path.macro_dir / f'{old_name}.json'
            file_path.rename(utils_path.macro_dir / f'{new_name}.json')
        except Exception as e:
            logger.error(f'重命名文件 报错信息：{e}')
            return False

    def open_folder(self, file_name: str):
        """
            打开文件所在文件夹
        Args:
            file_name (str): 宏文件文件名(不包含扩展名)
        """
        try:
            logger.info(f'打开文件所在文件夹：{file_name}')
            file_path = utils_path.macro_dir / f'{file_name}.json'
            subprocess.run(['explorer', '/select,', str(file_path.resolve())])
        except Exception as e:
            logger.error(f'打开文件所在文件夹 报错信息：{e}')
            return False

    def delete_file(self, file_name: str):
        """
            删除文件
        Args:
            file_name (str): 宏文件文件名(不包含扩展名)
        """
        try:
            logger.info(f'删除文件：{file_name}')
            file_path = utils_path.macro_dir / f'{file_name}.json'
            file_path.unlink()
        except Exception as e:
            logger.error(f'删除文件 报错信息：{e}')
            return False

    def get_memory_logs(self):
        """
            获取内存中的日志内容
        Returns:
            str: 日志内容
        """
        try:
            if hasattr(self, '_memory_handler') and self._memory_handler:
                return self._memory_handler.get_logs()
            return '日志系统未初始化'
        except Exception as e:
            logger.error(f'获取内存日志 报错信息：{e}')
            return False

    def get_memory_logs_count(self):
        """
            获取内存日志条目数量
        Returns:
            int: 日志条目数量
        """
        try:
            if hasattr(self, '_memory_handler') and self._memory_handler:
                return self._memory_handler.get_logs_count()
            return 0
        except Exception as e:
            logger.error(f'获取内存日志数量 报错信息：{e}')
            return 0

    def get_memory_logs_since(self, index):
        """
            获取从指定索引开始的增量日志
        Args:
            index: 起始索引位置
        Returns:
            dict: 包含日志内容和新索引位置的字典
        """
        try:
            if hasattr(self, '_memory_handler') and self._memory_handler:
                return self._memory_handler.get_logs_since(index)
            return {'content': '', 'new_index': 0}
        except Exception as e:
            logger.error(f'获取增量内存日志 报错信息：{e}')
            return {'content': '', 'new_index': 0}

    def clear_memory_logs(self):
        """
            清空内存中的日志
        """
        try:
            if hasattr(self, '_memory_handler') and self._memory_handler:
                self._memory_handler.clear_logs()
                logger.info('清空内存日志')
                return True
            return False
        except Exception as e:
            logger.error(f'清空内存日志 报错信息：{e}')
            return False

    def has_new_error(self):
        """
            检查是否有未读的错误
        Returns:
            bool: 是否有未读的错误
        """
        try:
            if hasattr(self, '_memory_handler') and self._memory_handler:
                return self._memory_handler.has_new_error()
            return False
        except Exception as e:
            logger.error(f'检查新错误 报错信息：{e}')
            return False

    def clear_new_error_flag(self):
        """
            清除新错误的标记
        """
        try:
            if hasattr(self, '_memory_handler') and self._memory_handler:
                self._memory_handler.clear_new_error_flag()
                return True
            return False
        except Exception as e:
            logger.error(f'清除错误标记 报错信息：{e}')
            return False


    # ------------------------------------------------------------------------------#
    # Key mapping file operations
    # ------------------------------------------------------------------------------#

    def get_key_mapping_files(self):
        mapping_dir = utils_path.key_mapping_dir
        mapping_dir.mkdir(parents=True, exist_ok=True)
        file_list = [f.stem for f in mapping_dir.glob('*.json') if f.suffix == '.json']
        if not file_list:
            default_data = {'version': 1, 'name': '默认配置', 'autoHideMouse': False, 'controls': [], 'dpad': [], 'swipes': []}
            with open(mapping_dir / '默认配置.json', 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)
            file_list = ['默认配置']
        return file_list

    def load_key_mapping_file(self, file_name):
        file_path = utils_path.key_mapping_dir / f'{file_name}.json'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'load_key_mapping_file error: {e}')
            return False

    def save_key_mapping_file(self, file_name, data):
        mapping_dir = utils_path.key_mapping_dir
        mapping_dir.mkdir(parents=True, exist_ok=True)
        file_path = mapping_dir / f'{file_name}.json'

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f'save_key_mapping_file error: {e}')
            return False

    def create_key_mapping_file(self):
        try:
            mapping_dir = utils_path.key_mapping_dir
            existing = [f.stem for f in mapping_dir.glob('*.json')]
            new_name = ''
            for i in range(1, 1000):
                name = f'新建键位{i}'
                if name not in existing:
                    new_name = name
                    break
            data = {'version': 1, 'name': new_name.replace('New_Keymap_','Keymap ').replace('_',' '), 'autoHideMouse': False, 'controls': [], 'dpad': [], 'swipes': []}
            with open(mapping_dir / f'{new_name}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return new_name
        except Exception as e:
            logger.error(f'create_key_mapping_file error: {e}')
            return False

    def rename_key_mapping_file(self, old_name, new_name):
        try:
            p = utils_path.key_mapping_dir / f'{old_name}.json'
            p.rename(utils_path.key_mapping_dir / f'{new_name}.json')
            return True
        except Exception as e:
            logger.error(f'rename_key_mapping_file error: {e}')
            return False

    def delete_key_mapping_file(self, file_name):
        try:
            p = utils_path.key_mapping_dir / f'{file_name}.json'
            p.unlink()
            return True
        except Exception as e:
            logger.error(f'delete_key_mapping_file error: {e}')
            return False
