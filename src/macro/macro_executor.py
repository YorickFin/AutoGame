import time
import logging
from threading import Thread
from autoxkit.mousekey import Mouse, KeyBoard
from autoxkit.constants import Hex_Key_Code

from ..services import services

logger = logging.getLogger(__name__)

HKC = Hex_Key_Code


class MacroExecutor:
    def __init__(self):
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

        self.function_names = ['固定连击', '宏', '截图', '追踪', '图像匹配', '颜色匹配', '文字识别']

        self.mouse = Mouse()
        self.keyboard = KeyBoard()

    @property
    def macro_switch(self):
        return services.macro.macro_switch

    @property
    def macro_window(self):
        return services.macro.macro_window

    @property
    def macro_file(self):
        return services.macro.macro_file

    @property
    def function_mapping_down(self):
        return services.macro.function_mapping_down

    def execute_macro(self, instruction: str, key_mouse_mode: str = 'send'):
        try:
            for action in instruction.split(','):
                if not self.macro_switch:
                    logger.info(f'手动关闭 完整指令：{instruction}')
                    return False
                action_list = action.strip().split()
                if not action_list:
                    continue
                len_al = len(action_list)
                handler = self.commands.get(action_list[0], self._click)
                handler(action_list, len_al, key_mouse_mode)
        except Exception as e:
            logger.error(f'执行错误 完整指令：{instruction}')
            raise e

    def _raise_error(self, error_msg):
        logger.error(error_msg)
        raise ValueError(error_msg)

    def _delay(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
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
                    matched_data = None
                    for data in self.macro_file:
                        if '名称' not in data:
                            continue
                        elif data['名称'] == action_list[0] and data['功能类型'] in self.function_names:
                            function = self.function_mapping_down.get(
                                data['功能类型'],
                                lambda _: logger.error(f'功能 {data["功能类型"]} 不存在')
                            )
                            matched_data = data
                            break
                    if function:
                        Thread(target=function, args=(matched_data,)).start()
                    else:
                        self._raise_error(f'单击指令参数错误：{action_list}')
            return True
        except Exception:
            self._raise_error(f'单击指令参数错误：{action_list}')

    def _down(self, action_list: list, len_al: int, key_mouse_mode: str = 'send'):
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