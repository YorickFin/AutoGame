import time
import ctypes
import numpy as np
from threading import Thread
from autoxkit.window import Window
from autoxkit.mousekey import Mouse, KeyBoard
from autoxkit.match import Match
from autoxkit.constants import Hex_Key_Code
from autoxkit.hook import HookListener, HotkeyListener, MouseEvent, KeyEvent

HKC = Hex_Key_Code

class Macro:
    def __init__(self, logger, ocr, path_manager):
        self.logger = logger
        self.ocr = ocr
        self.api = None

        # 使用统一的路径管理器
        self.path_manager = path_manager
        self.base_res_path = self.path_manager.base_res_path
        self.base_user_path = self.path_manager.base_user_path

        self.macro_window = None
        self.macro_switch = False
        self.macro_switch_key = None
        self.key_name = None
        self.macro_file = None
        self.down_state_keys = []  # 记录已经还在按下状态的按键，弹起清理，用来限制线程重复创建
        self.listening_for_key = False  # 是否正在监听按键输入
        self.listening_key_target = None  # 当前监听的目标 (type, id)
        self.last_key_pressed = None  # 最后按下的按键
        self.key_mapping_executor = None  # 按键映射执行器，用于 scrcpy 触摸事件
        self.button_mapping = {
            'MLeft': 0,
            'MRight': 1,
            'Middle': 2,
            'MSide1': 3,
            'MSide2': 4,
        }
        self.commands = {
            '按下': self._down,
            '弹起': self._up,
            '移动': self._move,
            '滚轮': self._wheel_scroll,
            '延迟': self._delay,
        }
        self.function_mapping_down = {
            '连击': lambda data: self.continuous(data),
            '固定连击': lambda data: self.fixed_continuous(data),
            '宏': lambda data: self.macros(data),
            '有序宏': lambda data: self.ordered_macros(data),
            '跟随': lambda data: self.follow(data, True),
            '组合': lambda data, args: self.combination(data, args),
            '映射': lambda data, args: self.mappings(data, args),
            '截图': lambda data: self.screenshot(data),
            '追踪': lambda data: self.track(data),
            '颜色匹配': lambda data: self.color_match(data),
            '图像匹配': lambda data: self.image_match(data),
            '文字识别': lambda data: self.text_ocr(data)
        }
        self.function_mapping_up = {
            '跟随': lambda data: self.follow(data, False)
        }
        self.function_names = ['固定连击', '宏', '截图', '追踪', '图像匹配', '颜色匹配', '文字识别']

        self.match = Match()
        self.mouse = Mouse()
        self.keyboard = KeyBoard()

        self.hook_listener = HookListener()
        self.hook_listener.add_handler('keydown', self._hook_all_down)
        self.hook_listener.add_handler('keyup', self._hook_all_up)
        self.hook_listener.add_handler('mousedown', self._hook_all_down)
        self.hook_listener.add_handler('mouseup', self._hook_all_up)

        self.hotkey_listener = HotkeyListener(self.hook_listener)
        self.hotkey_listener.add_hotkey('保存', ['LCtrl', 'S'], lambda: self._safe_save_json())
        self.hotkey_listener.add_hotkey('投屏全屏', ['F11'], lambda: self._safe_toggle_fullscreen())

#   --------------------------------------------------监听器控制-------------------------------------------------

    def start(self):
        """
            启动监听器
        """
        self.logger.info('键鼠监听器启动')
        self.hook_listener.start()

    def _safe_save_json(self):
        """安全保存 JSON 文件，处理窗口已关闭的情况"""
        try:
            if self.api:
                self.api.save_json_file()
        except Exception as e:
            self.logger.error(f'保存 JSON 文件失败: {e}')

    def _safe_toggle_fullscreen(self):
        """安全切换全屏，处理窗口已关闭的情况"""
        try:
            if self.api:
                self.api.toggle_screencast_fullscreen()
        except Exception as e:
            self.logger.error(f'切换全屏失败: {e}')

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
        mouse_icon_path = self.path_manager.cursor_path
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

    def set_api(self, api):
        """
            设置 API 引用
        Args:
            api: API 对象
        """
        self.api = api

    def set_key_mapping_executor(self, executor):
        """
            设置按键映射执行器
        Args:
            executor: KeyMappingExecutor 实例
        """
        self.key_mapping_executor = executor

    def set_macro_file(self, macro_file: dict):
        """
            设置宏文件
        Args:
            macro_file (dict): 宏文件内容字典
        """
        self.macro_file = macro_file

    def set_macro_switch_key(self, key: str):
        """
            设置宏开关按键
        Args:
            key (str): 宏开关按键
        """
        self.macro_switch_key = key

    def get_key_name(self):
        """
            获取当前按键名称
        Returns:
            str: 当前按键名称
        """
        return self.key_name

    def start_listening_key(self):
        """
            开始监听按键输入
        """
        self.listening_for_key = True
        self.last_key_pressed = None

    def stop_listening_key(self):
        """
            停止监听按键输入
        """
        self.listening_for_key = False
        self.last_key_pressed = None

    def get_last_key(self):
        """
            获取最后按下的按键
        Returns:
            str: 最后按下的按键名称，如果没有则返回 None
        """
        return self.last_key_pressed

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
        return self.match.get_pixel_color(x, y, is_return_hex=True)

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

    def execute_macro(self, instruction: str, key_mouse_mode: str = 'send'):
        """
            执行宏指令
        Args:
            instruction (str): 完整宏指令
        """
        try:
            for action in instruction.split(','):
                if not self.macro_switch:
                    self.logger.info(f'手动关闭 完整指令：{instruction}')
                    return False
                action_list = action.strip().split()
                if not action_list:
                    continue
                len_al = len(action_list)
                handler = self.commands.get(action_list[0], self._click)
                handler(action_list, len_al, key_mouse_mode)
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

    def _delay(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
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
                    if not self.macro_switch:
                        return False
                    time.sleep(1)
            if float_time > 0:
                time.sleep(float_time)
            return True
        except Exception:
            self._raise_error(f'延迟指令参数错误：{action_list}')

    def _click(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
        """
            单击指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
            key_mouse_mode (str): 'send', 'post', 'global'。默认 'send'
        """
        if len_al not in (1, 3):
            self._raise_error(f'单击指令参数个数错误，期望1或3，实际{len_al}：{action_list}')

        try:
            if len_al == 3 and action_list[0] in self.button_mapping:
                x, y = int(action_list[1]), int(action_list[2])
                button = self.button_mapping[action_list[0]]
                if self.macro_window:
                    self.macro_window.send_mouse_click(x=x, y=y, button=button, mode=key_mouse_mode)
                else:
                    self.mouse.mouse_click(x=x, y=y, button=button)
            elif len_al == 1:
                if action_list[0] in HKC:
                    if self.macro_window:
                        self.macro_window.send_key_click(key_name=action_list[0], mode=key_mouse_mode)
                    else:
                        self.keyboard.key_click(key_name=action_list[0])
                elif action_list[0] in self.button_mapping:
                    button = self.button_mapping[action_list[0]]
                    if self.macro_window:
                        self.macro_window.send_mouse_click(button=button, mode=key_mouse_mode)
                    else:
                        self.mouse.mouse_click(button=button)
                else:
                    function = None
                    for data in self.macro_file:
                        if '名称' not in data:
                            continue
                        elif data['名称'] == action_list[0]:
                            function = self.function_mapping_down.get(
                                data['功能类型'],
                                lambda _: self.logger.error(f'功能 {data["功能类型"]} 不存在')
                            )
                            break
                    if function:
                        function(data)
                    else:
                        self._raise_error(f'单击指令参数错误：{action_list}')
            return True
        except Exception:
            self._raise_error(f'单击指令参数错误：{action_list}')

    def _down(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
        """
            按下指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
            key_mouse_mode (str): 'send', 'post', 'global'。默认 'send'
        """
        if len_al not in (2, 4):
            self._raise_error(f'按键指令参数个数错误，期望2或4，实际{len_al}：{action_list}')

        try:
            if len_al == 2:
                if action_list[1] in HKC:
                    if self.macro_window:
                        self.macro_window.send_key_down(key_name=action_list[1], mode=key_mouse_mode)
                    else:
                        self.keyboard.key_down(key_name=action_list[1])
                elif action_list[1] in self.button_mapping:
                    button = self.button_mapping[action_list[1]]
                    if self.macro_window:
                        self.macro_window.send_mouse_down(button=button, mode=key_mouse_mode)
                    else:
                        self.mouse.mouse_down(button=button)
                else:
                    self._raise_error(f'按键指令参数错误：{action_list}')
            elif len_al == 4:
                x, y = int(action_list[2]), int(action_list[3])
                button = self.button_mapping[action_list[1]]
                if self.macro_window:
                    self.macro_window.send_mouse_down(x=x, y=y, button=button, mode=key_mouse_mode)
                else:
                    self.mouse.mouse_down(x=x, y=y, button=button)
            return True
        except Exception:
            self._raise_error(f'按键指令参数错误：{action_list}')

    def _up(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
        """
            弹起指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
            key_mouse_mode (str): 'send', 'post', 'global'。默认 'send'
        """
        if len_al not in (2, 4):
            self._raise_error(f'弹起指令参数个数错误，期望2或4，实际{len_al}：{action_list}')

        try:
            if len_al == 2:
                if action_list[1] in HKC:
                    if self.macro_window:
                        self.macro_window.send_key_up(key_name=action_list[1], mode=key_mouse_mode)
                    else:
                        self.keyboard.key_up(key_name=action_list[1])
                elif action_list[1] in self.button_mapping:
                    button = self.button_mapping[action_list[1]]
                    if self.macro_window:
                        self.macro_window.send_mouse_up(button=button, mode=key_mouse_mode)
                    else:
                        self.mouse.mouse_up(button=button)
                else:
                    self._raise_error(f'弹起指令参数错误：{action_list}')
            elif len_al == 4:
                x, y = int(action_list[2]), int(action_list[3])
                button = self.button_mapping[action_list[1]]
                if self.macro_window:
                    self.macro_window.send_mouse_up(x=x, y=y, button=button, mode=key_mouse_mode)
                else:
                    self.mouse.mouse_up(x=x, y=y, button=button)
            return True
        except Exception:
            self._raise_error(f'弹起指令参数错误：{action_list}')

    def _move(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
        """
            移动指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
            key_mouse_mode (str): 'send', 'post', 'global'。默认 'send'
        """
        if len_al not in (3, 4, 5):
            self._raise_error(f'移动指令参数个数错误，期望3~5，实际{len_al}：{action_list}')

        try:
            x, y = int(action_list[1]), int(action_list[2])
            duration = float(action_list[3]) if len_al >= 4 else 0.2
            steps = int(action_list[4]) if len_al == 5 else 10
            if self.macro_window:
                self.macro_window.send_mouse_move(x=x, y=y, duration=duration, steps=steps, mode=key_mouse_mode)
            else:
                self.mouse.mouse_move(x=x, y=y, duration=duration, steps=steps)
            return True
        except Exception:
            self._raise_error(f'移动指令参数错误：{action_list}')

    def _wheel_scroll(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
        """
            滚轮指令
        Args:
            action_list (list): 指令参数列表
            len_al (int): 指令参数数量
            key_mouse_mode (str): 'send', 'post', 'global'。默认 'send'
        """
        if len_al not in (2, 4):
            self._raise_error(f'滚轮指令参数个数错误，期望2或4，实际{len_al}：{action_list}')

        try:
            amount = int(action_list[1])
            x, y = int(action_list[2]) if len_al == 4 else None, \
                int(action_list[3]) if len_al == 4 else None
            if self.macro_window:
                self.macro_window.send_mouse_wheel(amount=amount, x=x, y=y, mode=key_mouse_mode)
            else:
                self.mouse.wheel_scroll(amount=amount, x=x, y=y)
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
            key_mouse_mode = data.get("键鼠模式", 'send')
            sleep_time = round(1 / (int(data['每秒次数'])), 4)
            while data['触发键'] in self.down_state_keys:
                self.execute_macro(data['宏指令'], key_mouse_mode)
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
            key_mouse_mode = data.get("键鼠模式", 'send')
            if '连击次数' in data and '连击间隔' in data:
                for _ in range(int(data['连击次数'])):
                    self.execute_macro(data['宏指令'], key_mouse_mode)
                    time.sleep(float(data['连击间隔']))
                if '后置指令' in data:
                    self.execute_macro(data['后置指令'], key_mouse_mode)
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
            key_mouse_mode = data.get("键鼠模式", 'send')
            self.execute_macro(data['宏指令'], key_mouse_mode)
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
            key_mouse_mode = data.get("键鼠模式", 'send')
            instruct = data['宏指令'].split(',')
            while data['触发键'] in self.down_state_keys:
                for macro in instruct:
                    if data['触发键'] not in self.down_state_keys:
                        return
                    self.execute_macro(macro, key_mouse_mode)
                    if '后置指令' in data:
                        self.execute_macro(data['后置指令'], key_mouse_mode)
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
            key_mouse_mode = data.get("键鼠模式", 'send')
            instruct = data['宏指令'].split(',')
            if state:
                for macro in instruct:
                    self.execute_macro(f'按下 {macro}', key_mouse_mode)
            else:
                for macro in instruct:
                    self.execute_macro(f'弹起 {macro}', key_mouse_mode)
        except Exception as e:
            self.logger.error(f'功能 跟随 报错信息：{e}')
            raise e

    def combination(self, data: dict, *args):
        """
            组合
        Args:
            data (dict): 组合数据
            *args: args参数
                auxiliary (str): 已按下辅助键
                auxiliary_n (str): 未按下辅助键
        """
        key_mappings = {
            '!辅助': args[0][1],
            '辅助': args[0][0],
        }
        print(key_mappings)
        self.logger.info(f'功能 组合 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            if '分支1' in data and '分支2' in data:
                if key_mappings['辅助'] == data['辅助1']:
                    instruction = data['分支1']
                    for old, new in key_mappings.items():
                        instruction = instruction.replace(old, new)
                    self.execute_macro(instruction, key_mouse_mode)
                else:
                    instruction = data['分支2']
                    for old, new in key_mappings.items():
                        instruction = instruction.replace(old, new)
                    self.execute_macro(instruction, key_mouse_mode)
            else:
                instruction = data['宏指令']
                for old, new in key_mappings.items():
                    instruction = instruction.replace(old, new)
                self.execute_macro(instruction, key_mouse_mode)
        except Exception as e:
            self.logger.error(f'功能 组合 报错信息：{e}')
            raise e

    def mappings(self, data: dict, *args):
        """
            映射
        Args:
            data (dict): 映射数据
            *args: args参数
                auxiliary (str): 已按下辅助键
                auxiliary_n (str): 未按下辅助键
                mapping (str): 已按下映射键
                mapping_n (str): 未按下映射键
        """
        key_mappings = {
            '!辅助': args[0][1],
            '辅助': args[0][0],
            '!映射': args[0][3],
            '映射': args[0][2],
        }
        self.logger.info(f'功能 映射 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            instruction = data['宏指令']
            for old, new in key_mappings.items():
                instruction = instruction.replace(old, new)
            self.execute_macro(instruction, key_mouse_mode)
        except Exception as e:
            self.logger.error(f'功能 映射 报错信息：{e}')
            raise e

    def screenshot(self, data: dict):
        """
            截图
        Args:
            data (dict): 截图数据
        """
        self.logger.info(f'功能 截图 data：{data}')
        try:
            image_name = data.get('文件名称', 'screenshot')
            if self.macro_window:
                window_width, window_height = self.macro_window.client_size
                rect = tuple(map(int, data.get('截图范围', f"0 0 {window_width} {window_height}").strip().split()))
                self.macro_window.screenshot(rect=rect, save_path=f'data\\target_image\\{image_name}.png')
            else:
                screen_width, screen_height = self.get_screen_size()
                rect = tuple(map(int, data.get('截图范围', f"0 0 {screen_width} {screen_height}").strip().split()))
                self.match.screenshot(rect=rect, save_path=f'data\\target_image\\{image_name}.png')
        except Exception as e:
            self.logger.error(f'功能 截图 报错信息：{e}')
            raise e

    def track(self, data: dict):
        """
            追踪
        Args:
            data (dict): 追踪数据
        """

        # 辅助函数：十六进制转RGB元组
        def hex_to_rgb(hex_color: str):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        # 辅助函数：验证矩形选区格式（宽或高必须为1）
        def verify_rect(rect):
            if len(rect) != 4:
                return False
            x1, y1, x2, y2 = rect
            if x1 >= x2 or y1 >= y2:
                return False
            width = x2 - x1
            height = y2 - y1
            return (width == 1) != (height == 1)

        self.logger.info(f'功能 追踪 data：{data}')
        try:
            target_color = data.get("目标颜色", None)
            if not target_color:
                self.logger.error(f'功能 追踪 错误信息：目标颜色缺失，当前数据：{data}')
                return
            target_color = hex_to_rgb(target_color)

            track_color = data.get("追踪颜色", None)
            if not track_color:
                self.logger.error(f'功能 追踪 错误信息：追踪颜色缺失，当前数据：{data}')
                return
            track_color = hex_to_rgb(track_color)

            rect = tuple(map(int, data.get('匹配范围', "None None None None").strip().split()))
            if 'None' in rect:
                self.logger.error(f'功能 追踪 错误信息：匹配范围缺失，当前数据：{data}')
                return
            if not verify_rect(rect):
                self.logger.error(f'功能 追踪 错误信息：匹配范围格式错误，当前数据：{data}')
                return

            key_mouse_mode = data.get("键鼠模式", 'send')
            offset = int(data.get("追踪补偿", 0))

            break_num = 10
            while break_num > 0:
                if self.macro_window:
                    np_colors = self.macro_window.screenshot(rect=rect)
                else:
                    np_colors = self.match.screenshot(rect=rect)

                # 统一形状为 (1, n, 3) 并获取像素一维数组
                np_colors = np_colors.reshape(1, -1, 3)
                pixels = np_colors[0]

                # 定位目标颜色
                target_mask = np.all(pixels == target_color, axis=-1)
                target_indices = np.where(target_mask)[0]
                if len(target_indices) == 0:
                    break_num -= 1
                    self.logger.info(f'功能 追踪 未找到目标颜色，剩余次数：{break_num}')
                    continue
                target_idx = target_indices[0]
                self.logger.info(f'功能 追踪 找到目标颜色，索引：{target_idx}')

                # 定位追踪颜色的头和尾
                track_mask = np.all(pixels == track_color, axis=-1)
                padded = np.pad(track_mask, (1, 1), constant_values=False)
                changes = np.diff(padded.astype(int))
                starts = np.where(changes == 1)[0]     # 各连续段的起始索引（在原数组中的位置）
                ends   = np.where(changes == -1)[0]    # 各连续段的结束索引的下一个位置
                if len(starts) == 0:
                    break_num -= 1
                    self.logger.info(f'功能 追踪 未找到追踪颜色，剩余次数：{break_num}')
                    continue
                head = starts[0] + offset
                tail = ends[-1] - offset
                self.logger.info(f'功能 追踪 找到追踪颜色，头索引：{head}，尾索引：{tail}')

                break_num = 10

                if head >= target_idx and '大于分支' in data:
                    self.execute_macro(data['大于分支'], key_mouse_mode)
                elif tail <= target_idx and '小于分支' in data:
                    self.execute_macro(data['小于分支'], key_mouse_mode)
                else:
                    time.sleep(0.2)

            self.logger.info('功能 追踪 结束')
            if '后置指令' in data:
                self.execute_macro(data['后置指令'], key_mouse_mode)
        except Exception as e:
            self.logger.error(f'功能 追踪 报错信息：{e}')
            raise e

    def color_match(self, data: dict):
        """
            颜色匹配
        Args:
            data (dict): 颜色匹配数据
        """
        self.logger.info(f'功能 颜色匹配 data：{data}')
        try:
            color_list = data.get("颜色", 'None').strip().split(',')
            if 'None' in color_list:
                self.logger.error(f'功能 颜色匹配 错误信息：颜色参数错误，预期颜色列表，当前数据：{data}')
                return
            coord_list = data.get("坐标", 'None').strip().split(',')
            if 'None' in coord_list:
                self.logger.error(f'功能 颜色匹配 错误信息：坐标参数错误，预期坐标列表，当前数据：{data}')
                return
            coord_list = [tuple(map(int, i.split())) for i in coord_list]

            if len(color_list) != len(coord_list):
                self.logger.error(f'功能 颜色匹配 错误信息：颜色数量与坐标数量不一致，当前数据：{data}')
                return

            key_mouse_mode = data.get("键鼠模式", 'send')
            similarity = float(data.get("相似度", 0.8))
            pattern = data.get("模式", 'all')
            if pattern not in ['all', 'any']:
                self.logger.error(f'功能 颜色匹配 错误信息：模式参数错误，预期all或any，当前数据：{data}')
                return

            flag = False
            for _, (coord, color) in enumerate(zip(coord_list, color_list)):
                if self.macro_window:
                    result, sim = self.macro_window.match_color(coord, color, similarity)
                else:
                    result, sim = self.match.match_color(coord, color, similarity)
                flag = result
                if flag and pattern == 'any':
                    break
                elif not flag and pattern == 'all':
                    break

            if flag and '分支Y' in data:
                self.execute_macro(data['分支Y'], key_mouse_mode)
            elif not flag and '分支N' in data:
                self.execute_macro(data['分支N'], key_mouse_mode)
        except Exception as e:
            self.logger.error(f'功能 颜色匹配 报错信息：{e}')
            raise e

    def image_match(self, data: dict):
        """
            图像匹配
        Args:
            data (dict): 图像匹配数据
        """
        self.logger.info(f'功能 图像匹配 data：{data}')
        try:
            target_image_path = data.get("图像名称", None)
            if not target_image_path:
                self.logger.error(f'功能 图像匹配 错误信息：图像名称缺失，当前数据：{data}')
                return
            if not target_image_path.exists():
                self.logger.error(f'功能 图像匹配 错误信息：图像文件不存在，当前数据：{data}')
                return

            key_mouse_mode = data.get("键鼠模式", 'send')
            similarity = float(data.get("相似度", 0.8))
            if self.macro_window:
                window_width, window_height = self.macro_window.client_size
                rect = tuple(map(int, data.get('匹配范围', f"0 0 {window_width} {window_height}").strip().split()))
            else:
                screen_width, screen_height = self.get_screen_size()
                rect = tuple(map(int, data.get('匹配范围', f"0 0 {screen_width} {screen_height}").strip().split()))

            if self.macro_window:
                target_image = self.macro_window.load_image(target_image_path)
                (x, y), sim = self.macro_window.match_image(target_image, rect, similarity)
            else:
                target_image = self.match.load_image(target_image_path)
                (x, y), sim = self.match.match_image(target_image, rect, similarity)
            if sim >= similarity and '分支Y' in data:
                if data.get('定位目标') == '是':
                    self.execute_macro(f'移动 {int(x)} {int(y)}', key_mouse_mode)
                self.execute_macro(data["分支Y"], key_mouse_mode)
            elif sim < similarity and '分支N' in data:
                self.execute_macro(data['分支N'], key_mouse_mode)
        except Exception as e:
            self.logger.error(f'功能 图像匹配 报错信息：{e}')
            raise e

    def text_ocr(self, data: dict):
        """
            文字识别
        Args:
            data (dict): 文字识别数据
        """
        self.logger.info(f'功能 文字识别 data：{data}')
        try:
            target_text = data.get("目标文本", 'None')
            if 'None' in target_text:
                self.logger.error(f'功能 文字识别 错误信息：目标文本参数错误，预期字符串，当前数据：{data}')
                return

            pattern = data.get("模式", 'all')
            if pattern not in ['all', 'any']:
                self.logger.error(f'功能 文字识别 错误信息：模式参数错误，预期all或any，当前数据：{data}')
                return

            key_mouse_mode = data.get("键鼠模式", 'send')
            if self.macro_window:
                window_width, window_height = self.macro_window.client_size
                rect = tuple(map(int, data.get('匹配范围', f"0 0 {window_width} {window_height}").strip().split()))
                target_image = self.macro_window.screenshot(rect=rect)
            else:
                screen_width, screen_height = self.get_screen_size()
                rect = tuple(map(int, data.get('匹配范围', f"0 0 {screen_width} {screen_height}").strip().split()))
                target_image = self.match.screenshot(rect=rect)

            ocr_result = self.ocr(target_image)

            x, y, flag = 0, 0, False
            for line in ocr_result:
                if pattern == 'all':
                    if line['text'] == target_text:
                        dx, dy = line['center']
                        x, y = dx + int(rect[0]), dy + int(rect[1])
                        flag = True
                        break
                elif pattern == 'any':
                    for line in ocr_result:
                        for char in line['text']:
                            if char in target_text:
                                dx, dy = line['center']
                                x, y = dx + int(rect[0]), dy + int(rect[1])
                                flag = True
                                break

            if flag and '分支Y' in data:
                if data.get('定位目标') == '是':
                    self.execute_macro(f'移动 {int(x)} {int(y)}', key_mouse_mode)
                self.execute_macro(data["分支Y"], key_mouse_mode)
            elif not flag and '分支N' in data:
                self.execute_macro(data['分支N'], key_mouse_mode)
        except Exception as e:
            self.logger.error(f'功能 文字识别 报错信息：{e}')
            raise e


#   --------------------------------------------------宏功能触发-------------------------------------------------

    def _macro_trigger(self):
        """
            宏功能触发
        """

        try:
            for data in self.macro_file:
                if '触发键' in data and '功能类型' in data:
                    if self.key_name == data['触发键'] and data['功能类型'] not in ['组合', '映射']:
                        function = self.function_mapping_down.get(
                            data['功能类型'],
                            lambda _: self.logger.error(f'功能 {data["功能类型"]} 不存在')
                        )
                        Thread(target=function, args=(data,)).start()
                        return

                    elif self.key_name == data['触发键'] and data['功能类型'] in ['组合', '映射']:
                        if data['辅助1'] in self.down_state_keys:
                            auxiliary = '辅助1'
                            auxiliary_n = '辅助2'
                            mapping = '映射1'
                            mapping_n = '映射2'

                        elif data['辅助2'] in self.down_state_keys:
                            auxiliary = '辅助2'
                            auxiliary_n = '辅助1'
                            mapping = '映射2'
                            mapping_n = '映射1'
                        else:
                            self.logger.error(f'功能 {data["功能类型"]} 错误信息：辅助键缺失，当前数据：{data}')
                            return False
                        function = self.function_mapping_down.get(
                            data['功能类型'],
                            lambda _, __: self.logger.error(f'功能 {data["功能类型"]} 不存在')
                        )
                        if data['功能类型'] == '组合':
                            args = data[auxiliary], data[auxiliary_n]
                        else:
                            args = data[auxiliary], data[auxiliary_n], data[mapping], data[mapping_n]
                        Thread(target=function, args=(data, args)).start()
                        return
        except Exception as e:
            self.logger.error(f'功能 {data["功能类型"]} 报错信息：{e}')
            return False

    def _switch_toggle(self):
        """
            宏开关切换触发
        """

        if self.macro_switch:
            # 连接到窗口
            if self.macro_file[0]['窗口标题'] or self.macro_file[0]['窗口类名']:
                try:
                    self.macro_window = Window(
                        title_name=self.macro_file[0]['窗口标题'],
                        class_name=self.macro_file[0]['窗口类名']
                    )
                    self.logger.info(f'连接窗口 成功 句柄信息：{self.macro_window.hwnd}')
                except Exception as e:
                    self.logger.error(f'连接窗口 报错信息：{e}')
                    self.macro_window = None
                    self.macro_switch = None
                    return False

            # 设置鼠标图标
            if self.macro_file[0].get('鼠标图标更改', '否') == '是':
                self.set_mouse_icon()

            # 禁用编辑器并保存文件
            if self.api:
                try:
                    self.api.disable_json_editor()
                    self.api.save_json_file()
                except Exception as e:
                    self.logger.error(f'切换宏开关时调用API失败: {e}')
        else:
            self.restore_mouse_icon()               # 恢复鼠标图标
            if self.api:
                try:
                    self.api.enable_json_editor()   # 启用编辑器
                except Exception as e:
                    self.logger.error(f'切换宏开关时调用API失败: {e}')
            self.macro_window = None                # 清除窗口对象
            self.match.clear_cache_images()         # 清除缓存图像

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

        if self.listening_for_key:
            self.last_key_pressed = self.key_name

        # if not self.path_manager.is_frozen():
        #     self.logger.info(f'键鼠监听器 按键按下：{self.key_name}')

        # 宏开关切换
        if self.key_name == self.macro_switch_key and self.macro_file:
            self.macro_switch = not self.macro_switch
            self.logger.info(f'宏开关切换：{self.macro_switch}')
            self._switch_toggle()

        # 按键映射执行器触发 (scrcpy 触摸事件)
        # 异常保护：避免钩子线程因按键映射执行器崩溃而全局失效
        try:
            if self.key_mapping_executor and self.key_mapping_executor.enabled:
                self.key_mapping_executor.on_key_down(self.key_name)
        except Exception as e:
            self.logger.error(f"按键映射执行器 on_key_down 异常: {e}", exc_info=True)

        # 宏功能触发
        if self.macro_switch and self.key_name not in self.down_state_keys:
            self.down_state_keys.append(self.key_name)
            self._macro_trigger()

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

        # if not self.path_manager.is_frozen():
        #     self.logger.info(f'键鼠监听器 按键弹起：{self.key_name}')

        # 按键映射执行器弹起事件 (scrcpy 触摸释放)
        # 异常保护：避免钩子线程因按键映射执行器崩溃而全局失效
        try:
            if self.key_mapping_executor and self.key_mapping_executor.enabled:
                self.key_mapping_executor.on_key_up(self.key_name)
        except Exception as e:
            self.logger.error(f"按键映射执行器 on_key_up 异常: {e}", exc_info=True)

        # 宏功能触发
        if self.macro_switch and self.key_name in self.down_state_keys:
            self.down_state_keys.remove(self.key_name)

            for data in self.macro_file:
                if '触发键' in data and '功能类型' in data:
                    if self.key_name == data['触发键'] and data['功能类型'] == '跟随':
                        function = self.function_mapping_up.get(
                            data['功能类型'],
                            lambda: self.logger.error(f'功能 {data["功能类型"]} 不存在')
                        )
                        Thread(target=function, args=(data,)).start()

        # 宏开关关闭时清空所有按键记录
        if not self.macro_switch:
            self.down_state_keys.clear()

        return False

    def __del__(self):
        self.stop()


