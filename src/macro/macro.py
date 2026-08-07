import ctypes
import logging
from threading import Thread
from autoxkit.window import Window
from autoxkit.match import Match
from autoxkit.hook import HookListener, HotkeyListener, MouseEvent, KeyEvent
from ..services import services
from .macro_executor import MacroExecutor
from .macro_functions import MacroFunctions

logger = logging.getLogger(__name__)


class Macro:
    def __init__(self):
        self.macro_window = None
        self.macro_switch = False
        self.macro_switch_key = None
        self.key_name = None
        self.macro_file = None
        self.down_state_keys = []
        self.auxiliary_history = {}
        self.set_cursor_flag = False
        self.listening_for_key = False
        self.listening_key_target = None
        self.last_key_pressed = None

        self.match = Match()
        self.executor = MacroExecutor()
        self.functions = MacroFunctions()

        self.hook_listener = HookListener()
        self.hook_listener.add_handler('keydown', self._hook_all_down)
        self.hook_listener.add_handler('keyup', self._hook_all_up)
        self.hook_listener.add_handler('mousedown', self._hook_all_down)
        self.hook_listener.add_handler('mouseup', self._hook_all_up)

        self.hotkey_listener = HotkeyListener(self.hook_listener)
        self.hotkey_listener.add_hotkey('保存', ['LCtrl', 'S'], lambda: self._safe_save_json())
        self.hotkey_listener.add_hotkey('投屏全屏', ['F11'], lambda: self._safe_toggle_fullscreen())

        self.function_mapping_down = {
            '连击': lambda data: self.functions.continuous(data),
            '固定连击': lambda data: self.functions.fixed_continuous(data),
            '宏': lambda data: self.functions.macros(data),
            '有序宏': lambda data: self.functions.ordered_macros(data),
            '自增': lambda data: self.functions.increment(data),
            '跟随': lambda data: self.functions.follow(data, True),
            '组合': lambda data, args: self.functions.combination(data, args),
            '映射': lambda data, args: self.functions.mappings(data, args),
            '截图': lambda data: self.functions.screenshot(data),
            '追踪': lambda data: self.functions.track(data),
            '颜色匹配': lambda data: self.functions.color_match(data),
            '图像匹配': lambda data: self.functions.image_match(data),
            '文字识别': lambda data: self.functions.text_ocr(data)
        }
        self.function_mapping_up = {
            '跟随': lambda data: self.functions.follow(data, False)
        }

    @property
    def _ocr(self):
        return services.ocr

    @property
    def _api(self):
        return services.api

    @property
    def _utils_path(self):
        return services.utils_path

    @property
    def _key_mapping(self):
        return services.key_mapping


    def start(self):
        logger.info('键鼠监听器启动')
        self.hook_listener.start()

    def _safe_save_json(self):
        try:
            if self._api:
                self._api.save_json_file()
        except Exception as e:
            logger.error(f'保存 JSON 文件失败: {e}')

    def _safe_toggle_fullscreen(self):
        try:
            if self._api:
                self._api.toggle_screencast_fullscreen()
        except Exception as e:
            logger.error(f'切换全屏失败: {e}')

    def stop(self):
        logger.info('键鼠监听器停止')
        self.hook_listener.stop()

    def set_mouse_icon(self):
        mouse_icon_path = self._utils_path.cursor_path
        try:
            if mouse_icon_path.exists():
                cursor = ctypes.windll.user32.LoadCursorFromFileW(str(mouse_icon_path))
                ctypes.windll.user32.SetSystemCursor(cursor, 32512)
                self.set_cursor_flag = True
                logger.info('设置鼠标图标')
        except Exception as e:
            logger.error(f'设置鼠标图标失败: {e}')

    def restore_mouse_icon(self):
        try:
            ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
            self.set_cursor_flag = False
            logger.info('恢复鼠标图标')
        except Exception as e:
            logger.error(f'恢复鼠标图标失败: {e}')

    def set_macro_file(self, macro_file: dict):
        self.macro_file = macro_file
        self.auxiliary_history.clear()

    def set_macro_switch_key(self, key: str):
        self.macro_switch_key = key

    def get_key_name(self):
        return self.key_name

    def start_listening_key(self):
        self.listening_for_key = True
        self.last_key_pressed = None

    def stop_listening_key(self):
        self.listening_for_key = False
        self.last_key_pressed = None

    def get_last_key(self):
        return self.last_key_pressed

    def get_mouse_position(self):
        return self.executor.mouse.get_mouse_position()

    def get_pixel_color(self):
        x, y = self.get_mouse_position()
        return self.match.get_pixel_color(x, y, is_return_hex=True)

    def get_screen_size(self):
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        return screen_width, screen_height

    def _macro_trigger(self):
        try:
            for data in self.macro_file:
                if '触发键' in data and '功能类型' in data:
                    if self.key_name == data['触发键'] and data['功能类型'] not in ['组合', '映射']:
                        function = self.function_mapping_down.get(
                            data['功能类型'],
                            lambda _: logger.error(f'功能 {data["功能类型"]} 不存在')
                        )
                        Thread(target=function, args=(data,)).start()
                        return

                    elif self.key_name == data['触发键'] and data['功能类型'] in ['组合', '映射']:
                        if data['辅助1'] in self.down_state_keys:
                            auxiliary = '辅助1'
                            auxiliary_n = '辅助2'
                            mapping = '映射1'
                            mapping_n = '映射2'
                            self.auxiliary_history[id(data)] = auxiliary

                        elif data['辅助2'] in self.down_state_keys:
                            auxiliary = '辅助2'
                            auxiliary_n = '辅助1'
                            mapping = '映射2'
                            mapping_n = '映射1'
                            self.auxiliary_history[id(data)] = auxiliary

                        else:
                            auxiliary = self.auxiliary_history.get(id(data))
                            if auxiliary == '辅助1':
                                auxiliary_n = '辅助2'
                                mapping = '映射1'
                                mapping_n = '映射2'
                            elif auxiliary == '辅助2':
                                auxiliary_n = '辅助1'
                                mapping = '映射2'
                                mapping_n = '映射1'
                            else:
                                logger.error(f'功能 {data["功能类型"]} 错误信息：辅助键缺失且无历史记录，当前数据：{data}')
                                continue
                        function = self.function_mapping_down.get(
                            data['功能类型'],
                            lambda _, __: logger.error(f'功能 {data["功能类型"]} 不存在')
                        )
                        if data['功能类型'] == '组合':
                            args = data[auxiliary], data[auxiliary_n]
                        else:
                            args = data[auxiliary], data[auxiliary_n], data[mapping], data[mapping_n]
                        Thread(target=function, args=(data, args)).start()
                        return
        except Exception as e:
            logger.error(f'功能 {data["功能类型"]} 报错信息：{e}')
            return False

    def _switch_toggle(self):
        if self.macro_switch:
            if self.macro_file[0]['窗口标题'] or self.macro_file[0]['窗口类名']:
                try:
                    self.macro_window = Window(
                        title_name=self.macro_file[0]['窗口标题'],
                        class_name=self.macro_file[0]['窗口类名']
                    )
                    logger.info(f'连接窗口 成功 句柄信息：{self.macro_window.hwnd}')
                except Exception as e:
                    logger.error(f'连接窗口 报错信息：{e}')
                    self.macro_window = None
                    self.macro_switch = None
                    return False

            if self.macro_file[0].get('鼠标图标更改', '否') == '是':
                self.set_mouse_icon()

            if self.macro_file[0].get('兼容模式', '否') == '是':
                self.executor.keyboard.compat = True
                self.executor.mouse.compat = True
            else:
                self.executor.keyboard.compat = False
                self.executor.mouse.compat = False

            if self._api:
                try:
                    self._api.disable_json_editor()
                    self._api.save_json_file()
                except Exception as e:
                    logger.error(f'切换宏开关时调用API失败: {e}')
        else:
            self.restore_mouse_icon()
            if self._api:
                try:
                    self._api.enable_json_editor()
                except Exception as e:
                    logger.error(f'切换宏开关时调用API失败: {e}')
            self.macro_window = None
            self.match.clear_cache_images()

    def _hook_all_down(self, event: KeyEvent | MouseEvent):
        if isinstance(event, KeyEvent):
            self.key_name = event.key_name
        elif isinstance(event, MouseEvent):
            self.key_name = event.button

        if self.listening_for_key:
            self.last_key_pressed = self.key_name

        if self.key_name == self.macro_switch_key and self.macro_file:
            self.macro_switch = not self.macro_switch
            logger.info(f'宏开关切换：{self.macro_switch}')
            self._switch_toggle()

        try:
            if self._key_mapping and self._key_mapping.enabled:
                self._key_mapping.on_key_down(self.key_name)
        except Exception as e:
            logger.error(f"按键映射执行器 on_key_down 异常: {e}", exc_info=True)

        if self.macro_switch and self.key_name not in self.down_state_keys:
            self.down_state_keys.append(self.key_name)
            self._macro_trigger()

        return False

    def _hook_all_up(self, event: KeyEvent | MouseEvent):
        if isinstance(event, KeyEvent):
            self.key_name = event.key_name
        elif isinstance(event, MouseEvent):
            self.key_name = event.button

        try:
            if self._key_mapping and self._key_mapping.enabled:
                self._key_mapping.on_key_up(self.key_name)
        except Exception as e:
            logger.error(f"按键映射执行器 on_key_up 异常: {e}", exc_info=True)

        if self.macro_switch and self.key_name in self.down_state_keys:
            self.down_state_keys.remove(self.key_name)

            for data in self.macro_file:
                if '触发键' in data and '功能类型' in data:
                    if self.key_name == data['触发键'] and data['功能类型'] == '跟随':
                        function = self.function_mapping_up.get(
                            data['功能类型'],
                            lambda: logger.error(f'功能 {data["功能类型"]} 不存在')
                        )
                        Thread(target=function, args=(data,)).start()

        if not self.macro_switch:
            self.down_state_keys.clear()

        return False


    def __del__(self):
        self.stop()
