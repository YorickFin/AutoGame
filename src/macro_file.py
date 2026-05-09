import json
import ast
from pathlib import Path

class MacroFile:
    def __init__(self, logger, macro):
        self.logger = logger
        self.macro = macro

        self.macro_dir = Path(r'data\macrofile')


    def get_macro_files(self):
        """
            获取 dir 下的所有 json 文件
        Returns:
            list: 所有 json 文件名列表(不包含扩展名)
        """
        file_list = [f.stem for f in self.macro_dir.glob('*.json') if f.suffix == '.json']
        self.logger.info(f'宏文件列表：{file_list}')
        return file_list

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
                dict: 宏文件内容字典
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
                raise e

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
                raise e

        try:
            file_path = self.macro_dir / f'{file_name}.json'
            macro_file = preprocess_file(macro_file)
            save_file(macro_file, file_path)
            self.macro.set_macro_file(macro_file)
            return macro_file
        except Exception as e:
            self.logger.error(f'保存宏文件 报错信息：{e}')
            return False

