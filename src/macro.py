import time
import ctypes
from pathlib import Path
from threading import Thread
from autoxkit import (HookListener, MouseEvent, KeyEvent,
                    Mouse, KeyBoard, MatchColor, MatchImage,
                    Hex_Key_Code)

HKC = Hex_Key_Code

class Macro:
    def __init__(self, logger, ocr):
        self.logger = logger
        self.ocr = ocr

        self.main_switch = False
        self.main_switch_key = None
        self.key_name = None
        self.macro_file = None
        self.down_state_keys = []  # 记录已经还在按下状态的按键，弹起清理，用来限制线程重复创建
        self.button_mapping = {
            'MLeft': 0,
            'MRight': 1,
            'Middle': 2,
            'side1': 3,
            'side2': 4,
        }
        self.commands = {
            '按下': self._down,
            '弹起': self._up,
            '移动': self._move,
            '滚轮': self._wheel_scroll,
            '延迟': self._delay,
        }

        self.mouse = Mouse()
        self.keyboard = KeyBoard()
        self.match_color = MatchColor()
        self.match_image = MatchImage()
        self.hook_listener = HookListener()
        self.hook_listener.add_handler('keydown', self._hook_all_down)
        self.hook_listener.add_handler('keyup', self._hook_all_up)
        self.hook_listener.add_handler('mousedown', self._hook_all_down)
        self.hook_listener.add_handler('mouseup', self._hook_all_up)


#   --------------------------------------------------监听器控制-------------------------------------------------

    def start(self):
        """
            启动监听器
        """
        self.logger.info('键鼠监听器启动')
        self.hook_listener.start()

    def stop(self):
        """
            停止监听器
        """
        self.logger.info('键鼠监听器停止')
        self.hook_listener.stop()


#   -------------------------------------------------鼠标图标管理-------------------------------------------------

    def set_mouse_icon(self):
        """
            设置鼠标图标
        """
        mouse_icon_path = Path(r'data\config\CursorNormal.cur')
        try:
            if mouse_icon_path.exists():
                cursor = ctypes.windll.user32.LoadCursorFromFileW(str(mouse_icon_path))
                ctypes.windll.user32.SetSystemCursor(cursor, 32512)
                self.logger.info('设置鼠标图标')
        except Exception as e:
            self.logger.error(f'设置鼠标图标失败: {e}')

    def restore_mouse_icon(self):
        """
            恢复鼠标图标
        """
        try:
            ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
            self.logger.info('恢复鼠标图标')
        except Exception as e:
            self.logger.error(f'恢复鼠标图标失败: {e}')

#   --------------------------------------------------类属性设置-------------------------------------------------

    def set_macro_file(self, macro_file: dict):
        """
            设置宏文件
        Args:
            macro_file (dict): 宏文件内容字典
        """
        self.macro_file = macro_file

    def set_main_switch_key(self, key: str):
        """
            设置主开关按键
        Args:
            key (str): 主开关按键
        """
        print(key)
        self.main_switch_key = key

    def get_key_name(self):
        """
            获取当前按键名称
        Returns:
            str: 当前按键名称
        """
        return self.key_name

    def get_mouse_position(self):
        """
            获取鼠标鼠标位置
        Returns:
            tuple: 鼠标位置元组
        """
        return self.mouse.get_mouse_position()

    def get_pixel_color(self):
        """
            获取指定像素的颜色
        Returns:
            tuple: 像素颜色元组
        """
        x, y = self.get_mouse_position()
        return self.match_color.get_pixel_color(x, y, is_return_hex=True)

    def get_screen_size(self):
        """
            获取屏幕分辨率
        Returns:
            tuple: 屏幕分辨率元组
        """
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        return screen_width, screen_height


#   --------------------------------------------------宏指令执行-------------------------------------------------

    def execute_macro(self, instruction: str):
        """
            执行宏指令
        Args:
            instruction (str): 完整宏指令
        """
        try:
            for action in instruction.split(','):
                if not self.main_switch:
                    self.logger.info(f'手动关闭 完整指令：{instruction}')
                    return False

                action_list = action.strip().split()
                if not action_list:
                    continue
                len_al = len(action_list)

                handler = self.commands.get(action_list[0], self._click)
                handler(action_list, len_al)
        except Exception as e:
            self.logger.error(f'执行错误 完整指令：{instruction}')
            raise e

    def _raise_error(self, error_msg):
        """
            报错处理
        Args:
            error_msg (str): 报错信息
        """
        self.logger.error(error_msg)
        raise ValueError(error_msg)

    def _delay(self, action_list: list, len_al: int):
        """
            延迟指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
        """
        if len_al != 2:
            self._raise_error(f'延迟指令参数个数错误，期望2，实际{len_al}：{action_list}')

        try:
            dtime = float(action_list[1])
            int_time = int(dtime)
            float_time = round(dtime - int_time, 4)
            if int_time >= 1:
                for _ in range(int_time):
                    if not self.main_switch:
                        return False
                    time.sleep(1)
            if float_time > 0:
                time.sleep(float_time)
            return True
        except Exception:
            self._raise_error(f'延迟指令参数错误：{action_list}')

    def _click(self, action_list: list, len_al: int):
        """
            单击指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
        """
        if len_al not in (1, 3):
            self._raise_error(f'单击指令参数个数错误，期望1或3，实际{len_al}：{action_list}')

        try:
            if len_al == 3 and action_list[0] in self.button_mapping:
                x, y = int(action_list[1]), int(action_list[2])
                button = self.button_mapping[action_list[0]]
                self.mouse.mouse_click(x=x, y=y, button=button)
            elif len_al == 1:
                if action_list[0] in HKC:
                    self.keyboard.key_click(action_list[0])
                elif action_list[0] in self.button_mapping:
                    button = self.button_mapping[action_list[0]]
                    self.mouse.mouse_click(button=button)
                else:
                    self._raise_error(f'单击指令参数错误：{action_list}')
            return True
        except Exception:
            self._raise_error(f'单击指令参数错误：{action_list}')

    def _down(self, action_list: list, len_al: int):
        """
            按下指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
        """
        if len_al not in (2, 4):
            self._raise_error(f'按键指令参数个数错误，期望2或4，实际{len_al}：{action_list}')

        try:
            if len_al == 2:
                if action_list[1] in HKC:
                    self.keyboard.key_down(action_list[1])
                elif action_list[1] in self.button_mapping:
                    button = self.button_mapping[action_list[1]]
                    self.mouse.mouse_down(button=button)
                else:
                    self._raise_error(f'按键指令参数错误：{action_list}')
            elif len_al == 4:
                x, y = int(action_list[1]), int(action_list[2])
                button = self.button_mapping[action_list[0]]
                self.mouse.mouse_down(x=x, y=y, button=button)
            return True
        except Exception:
            self._raise_error(f'按键指令参数错误：{action_list}')

    def _up(self, action_list: list, len_al: int):
        """
            弹起指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
        """
        if len_al not in (2, 4):
            self._raise_error(f'弹起指令参数个数错误，期望2或4，实际{len_al}：{action_list}')

        try:
            if len_al == 2:
                if action_list[1] in HKC:
                    self.keyboard.key_up(action_list[1])
                elif action_list[1] in self.button_mapping:
                    button = self.button_mapping[action_list[1]]
                    self.mouse.mouse_up(button=button)
                else:
                    self._raise_error(f'弹起指令参数错误：{action_list}')
            elif len_al == 4:
                x, y = int(action_list[1]), int(action_list[2])
                button = self.button_mapping[action_list[0]]
                self.mouse.mouse_up(x=x, y=y, button=button)
            return True
        except Exception:
            self._raise_error(f'弹起指令参数错误：{action_list}')

    def _move(self, action_list: list, len_al: int):
        """
            移动指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
        """
        if len_al not in (3, 4, 5):
            self._raise_error(f'移动指令参数个数错误，期望3~5，实际{len_al}：{action_list}')

        try:
            x, y = int(action_list[1]), int(action_list[2])
            duration = float(action_list[3]) if len_al >= 4 else 0.2
            steps = int(action_list[4]) if len_al == 5 else 10
            self.mouse.mouse_move(x, y, duration, steps)
            return True
        except Exception:
            self._raise_error(f'移动指令参数错误：{action_list}')

    def _wheel_scroll(self, action_list: list, len_al: int):
        """
            滚轮指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
        """
        if len_al not in (2, 4):
            self._raise_error(f'滚轮指令参数个数错误，期望2或4，实际{len_al}：{action_list}')

        try:
            amount = int(action_list[1])
            x, y = int(action_list[2]) if len_al == 4 else None, \
                int(action_list[3]) if len_al == 4 else None
            self.mouse.wheel_scroll(amount, x, y)
            return True
        except Exception:
            self._raise_error(f'滚轮指令参数错误：{action_list}')


#   --------------------------------------------------宏功能实现-------------------------------------------------

    def continuous(self, data: dict):
        """
            连击
        Args:
            data (dict): 连击数据
        """
        self.logger.info(f'功能 连击 data：{data}')
        try:
            sleep_time = round(1 / (int(data['每秒次数'])), 4)
            while data['触发键'] in self.down_state_keys:
                if data['宏指令'] in HKC or data['宏指令'] in self.button_mapping:
                    self.execute_macro(data['宏指令'])
                time.sleep(sleep_time)
        except Exception as e:
            self.logger.error(f'功能 连击 报错信息：{e}')
            raise e

    def fixed_continuous(self, data: dict):
        """
            固定连击
        Args:
            data (dict): 固定连击数据
        """
        self.logger.info(f'功能 固定连击 data：{data}')
        try:
            if '连击次数' in data and '连击间隔' in data:
                for _ in range(int(data['连击次数'])):
                    self.execute_macro(data['宏指令'])
                    time.sleep(int(data['连击间隔']))
                if '后置指令' in data:
                    self.execute_macro(data['后置指令'])
            else:
                self.logger.error(f'功能 固定连击 错误信息：连击次数或连击间隔缺失，当前数据：{data}')
        except Exception as e:
            self.logger.error(f'功能 固定连击 报错信息：{e}')
            raise e

    def macros(self, data: dict):
        """
            宏
        Args:
            data (dict): 宏数据
        """
        self.logger.info(f'功能 宏 data：{data}')
        try:
            self.execute_macro(data['宏指令'])
        except Exception as e:
            self.logger.error(f'功能 宏 报错信息：{e}')
            raise e

    def ordered_macros(self, data: dict):
        """
            有序宏
        Args:
            data (dict): 有序宏数据
        """
        self.logger.info(f'功能 有序宏 data：{data}')
        try:
            instruct = data['宏指令'].split(',')
            while data['触发键'] in self.down_state_keys:
                for macro in instruct:
                    self.execute_macro(macro)
                    if '后置指令' in data:
                        self.execute_macro(data['后置指令'])
        except Exception as e:
            self.logger.error(f'功能 有序宏 报错信息：{e}')
            raise e

    def follow(self, data: dict, state: bool):
        """
            跟随
        Args:
            data (dict): 跟随数据
            state (bool): 是否按下
        """
        self.logger.info(f'功能 跟随 data：{data}')
        try:
            if state:
                self.execute_macro(f'按下 {data["宏指令"]}')
            else:
                self.execute_macro(f'弹起 {data["宏指令"]}')
        except Exception as e:
            self.logger.error(f'功能 跟随 报错信息：{e}')
            raise e

    def combination(self, data: dict, auxiliary: str, auxiliary_n: str):
        """
            组合
        Args:
            data (dict): 组合数据
            auxiliary (str): 辅助键
            auxiliary_n (str): 辅助键2
        """
        key_mappings = {
            '辅助': auxiliary,
            '!辅助': auxiliary_n,
        }
        self.logger.info(f'功能 组合 data：{data}')
        try:
            if '分支1' in data and '分支2' in data:
                if key_mappings['辅助'] == data['辅助1']:
                    instruction = data['分支1']
                    for old, new in key_mappings.items():
                        instruction = instruction.replace(old, new)
                    self.execute_macro(instruction)
                else:
                    instruction = data['分支2']
                    for old, new in key_mappings.items():
                        instruction = instruction.replace(old, new)
                    self.execute_macro(instruction)
            else:
                instruction = data['宏指令']
                for old, new in key_mappings.items():
                    instruction = instruction.replace(old, new)
                self.execute_macro(instruction)
        except Exception as e:
            self.logger.error(f'功能 组合 报错信息：{e}')
            raise e

    def mappings(self, data: dict, auxiliary: str, auxiliary_n: str, mapping: str, mapping_n: str):
        """
            映射
        Args:
            data (dict): 映射数据
            auxiliary (str): 辅助键
            auxiliary_n (str): 辅助键2
            mapping (str): 映射键
            mapping_n (str): 映射键2
        """
        key_mappings = {
            '辅助': auxiliary,
            '!辅助': auxiliary_n,
            '映射': mapping,
            '!映射': mapping_n,
        }
        self.logger.info(f'功能 映射 data：{data}')
        try:
            instruction = data['宏指令']
            for old, new in key_mappings.items():
                instruction = instruction.replace(old, new)
            self.execute_macro(instruction)
        except Exception as e:
            self.logger.error(f'功能 映射 报错信息：{e}')
            raise e

    def image_match(self, data: dict):
        """
            图像匹配
        Args:
            data (dict): 图像匹配数据
        """
        self.logger.info(f'功能 图像匹配 data：{data}')
        try:
            if '图像名称' not in data:
                self.logger.error(f'功能 图像匹配 错误信息：图像名称缺失，当前数据：{data}')
                return

            target_image = Path(r'data\target_image') / data['图像名称']
            if not target_image.exists():
                self.logger.error(f'功能 图像匹配 错误信息：图像文件不存在，当前数据：{data}')
                return

            self.match_image.match(target_image)
        except Exception as e:
            self.logger.error(f'功能 图像匹配 报错信息：{e}')
            raise e

    def color_match(self, data: dict):
        """
            颜色匹配
        Args:
            data (dict): 颜色匹配数据
        """
        self.logger.info(f'功能 颜色匹配 data：{data}')
        try:
            self.execute_macro(data['宏指令'])
        except Exception as e:
            self.logger.error(f'功能 颜色匹配 报错信息：{e}')
            raise e

    def text_ocr(self, data: dict):
        """
            文字识别
        Args:
            data (dict): 文字识别数据
        """
        self.logger.info(f'功能 文字识别 data：{data}')
        try:
            self.execute_macro(data['宏指令'])
        except Exception as e:
            self.logger.error(f'功能 文字识别 报错信息：{e}')
            raise e


#   --------------------------------------------------宏功能触发-------------------------------------------------

    def _hook_all_down(self, event: KeyEvent | MouseEvent):
        """
            所有键按下事件
        Args:
            event (KeyEvent | MouseEvent): 事件对象
        """
        if isinstance(event, KeyEvent):
            self.key_name = event.key_name
        elif isinstance(event, MouseEvent):
            self.key_name = event.button
        print(self.key_name)

        # 主开关切换
        if self.key_name == self.main_switch_key and self.macro_file:
            self.main_switch = not self.main_switch
            # 检查是否需要更改鼠标图标
            if self.main_switch and self.macro_file[0].get('鼠标图标更改', '否') == '是':
                    self.set_mouse_icon()
            else:
                self.restore_mouse_icon()

        # 主开关开启时
        if self.main_switch:
            if self.key_name in self.down_state_keys:
                return False
            else:
                self.down_state_keys.append(self.key_name)

        return False


    def _hook_all_up(self, event: KeyEvent | MouseEvent):
        """
            所有键弹起事件
        Args:
            event (KeyEvent | MouseEvent): 事件对象
        """
        if isinstance(event, KeyEvent):
            self.key_name = event.key_name
        elif isinstance(event, MouseEvent):
            self.key_name = event.button
        print(self.key_name)

        if self.key_name in self.down_state_keys:
            self.down_state_keys.remove(self.key_name)
        if not self.main_switch:
            self.down_state_keys.clear()

        return False

    def __del__(self):
        self.stop()


if __name__ == '__main__':
    macro = Macro(None)
    macro.hook_listener.wait()