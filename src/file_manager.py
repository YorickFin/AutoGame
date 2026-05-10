import json
import ast
import subprocess
from pathlib import Path

class FileManager:

    def __init__(self, logger, macro):
        self.logger = logger
        self.macro = macro

        self.file_list = []
        self.new_file_content = [
            {
                '备注': '基本信息',
                '按键更改': '',
                '坐标更改': f'{self.macro.get_screen_size()}',
                '鼠标图标更改': '是'
            }
        ]
        self.macro_dir = Path(r'data\macrofile')
        self.config = {}
        self.config_path = Path(r'data\config\config.json')

    def load_config_file(self):
        """
            加载配置文件
        Returns:
            dict | False: 配置文件内容字典 | False
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f'加载配置文件 报错信息：{e}')
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
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            self.logger.error(f'保存配置文件 报错信息：{e}')
            return False

    def get_macro_files(self):
        """
            获取 dir 下的所有 json 文件
        Returns:
            list: 所有 json 文件名列表(不包含扩展名)
        """
        self.file_list = [f.stem for f in self.macro_dir.glob('*.json') if f.suffix == '.json']
        self.logger.info(f'宏文件列表：{self.file_list}')
        return self.file_list

    def load_macro_file(self, file_name: str):
        """
            加载宏文件
        Args:
            file_name (str): 宏文件名(不包含扩展名)
        Returns:
            dict | False: 宏文件内容字典 | False
        """
        self.logger.info(f'加载宏文件：{file_name}')
        file_path = self.macro_dir / f'{file_name}.json'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                macro_file = json.load(f)
            self.macro.set_macro_file(macro_file)
            return macro_file
        except Exception as e:
            self.logger.error(f'加载宏文件 报错信息：{e}')
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
                self.logger.error(f'预处理宏文件 报错信息：{e}')
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
                self.logger.error(f'保存宏文件 报错信息：{e}')
                return False

        try:
            file_path = self.macro_dir / f'{file_name}.json'
            macro_file = preprocess_file(macro_file)
            save_file(macro_file, file_path)
            self.macro.set_macro_file(macro_file)
            return macro_file
        except Exception as e:
            self.logger.error(f'保存宏文件 报错信息：{e}')
            return False

    def create_new_file(self):
        """
            创建新文件
        """
        try:
            new_file_name = ''
            for i in range(1, 1000):
                if f'新建文件{i}' not in self.file_list:
                    new_file_name = f'新建文件{i}'
                    break
            with open(self.macro_dir / f'{new_file_name}.json', 'w', encoding='utf-8') as f:
                json.dump(self.new_file_content, f, ensure_ascii=False, indent=4)
            self.logger.info(f'创建新文件：{new_file_name}')
        except Exception as e:
            self.logger.error(f'创建新文件 报错信息：{e}')
            return False

    def rename_file(self, old_name: str, new_name: str):
        """
            重命名文件
        Args:
            old_name (str): 旧文件名(不包含扩展名)
            new_name (str): 新文件名(不包含扩展名)
        """
        try:
            file_path = self.macro_dir / f'{old_name}.json'
            file_path.rename(self.macro_dir / f'{new_name}.json')
            self.logger.info(f'重命名文件：{old_name} -> {new_name}')
        except Exception as e:
            self.logger.error(f'重命名文件 报错信息：{e}')
            return False

    def open_folder(self, file_name: str):
        """
            打开文件夹
        """
        try:
            file_path = self.macro_dir / f'{file_name}.json'
            subprocess.run(['explorer', f'/select,{file_path}'])
            self.logger.info(f'打开文件夹：{file_name}')
        except Exception as e:
            self.logger.error(f'打开文件夹 报错信息：{e}')
            return False

    def delete_file(self, file_name: str):
        """
            删除文件
        Args:
            file_name (str): 宏文件文件名(不包含扩展名)
        """
        try:
            file_path = self.macro_dir / f'{file_name}.json'
            file_path.unlink()
            self.logger.error(f'删除文件：{file_name}')
        except Exception as e:
            self.logger.error(f'删除文件 报错信息：{e}')
            return False

    def set_memory_handler(self, handler):
        """
            设置内存日志处理器
        Args:
            handler: MemoryLogHandler实例
        """
        self._memory_handler = handler

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
            self.logger.error(f'获取内存日志 报错信息：{e}')
            return False

    def clear_memory_logs(self):
        """
            清空内存中的日志
        """
        try:
            if hasattr(self, '_memory_handler') and self._memory_handler:
                self._memory_handler.clear_logs()
                self.logger.info('清空内存日志')
                return True
            return False
        except Exception as e:
            self.logger.error(f'清空内存日志 报错信息：{e}')
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
            self.logger.error(f'检查新错误 报错信息：{e}')
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
            self.logger.error(f'清除错误标记 报错信息：{e}')
            return False
