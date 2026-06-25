import logging
import math
import subprocess
import sys

from ..services import services


logger = logging.getLogger(__name__)


class BackendApi:
    def __init__(self):
        self._no_key_names = ['Middle', 'MSide1', 'MSide2']
        self._maximized = False

    @property
    def _macro(self):
        return services.macro

    @property
    def _utils_file(self):
        return services.utils_file

    @property
    def _scrcpy_manager(self):
        return services.scrcpy_manager

    @property
    def _key_mapping(self):
        return services.key_mapping

    def get_config_file(self):
        """
        Desc:
            加载配置文件，并设置宏开关按键
        Returns:
            dict: 配置字典，包含 macroSwitch 等配置项
        """
        config = self._utils_file.load_config_file()
        self._macro.set_macro_switch_key(config['macroSwitch'])
        return config

    def save_config_file(self, config):
        """
        Desc:
            保存配置文件，同时更新宏开关按键
        Args:
            config (dict): 配置字典
        Returns:
            bool: 保存是否成功
        """
        self._macro.set_macro_switch_key(config['macroSwitch'])
        return self._utils_file.save_config_file(config)

    def get_phone_input_state(self):
        """
        Desc:
            获取手机输入状态，包括键盘显示状态和是否刚隐藏
        Returns:
            dict: 包含 keyboard_shown 和 just_hidden 两个字段
        """
        km = self._key_mapping
        return {
            "keyboard_shown": km.keyboard_shown if km else None,
            "just_hidden": km.read_and_clear_just_hidden() if km else False,
        }

    def get_macro_files(self):
        """
        Desc:
            获取宏文件列表
        Returns:
            list: 宏文件名列表
        """
        return self._utils_file.get_macro_files()

    def load_macrofile(self, file_name: str):
        """
        Desc:
            加载指定的宏文件
        Args:
            file_name (str): 宏文件名
        Returns:
            dict: 宏文件内容
        """
        return self._utils_file.load_macro_file(file_name)

    def save_macrofile(self, file_name: str, macro_file: str):
        """
        Desc:
            保存宏文件
        Args:
            file_name (str): 宏文件名
            macro_file (str): 宏文件内容
        Returns:
            bool: 保存是否成功
        """
        return self._utils_file.save_macro_file(file_name, macro_file)

    def create_new_file(self):
        """
        Desc:
            创建新的宏文件
        Returns:
            str: 创建的文件名
        """
        return self._utils_file.create_new_file()

    def rename_file(self, old_name: str, new_name: str):
        """
        Desc:
            重命名文件
        Args:
            old_name (str): 原文件名
            new_name (str): 新文件名
        Returns:
            bool: 重命名是否成功
        """
        return self._utils_file.rename_file(old_name, new_name)

    def open_folder(self, file_name: str):
        """
        Desc:
            在文件管理器中打开指定文件所在的文件夹
        Args:
            file_name (str): 文件名
        """
        return self._utils_file.open_folder(file_name)

    def delete_file(self, file_name: str):
        """
        Desc:
            删除指定的文件
        Args:
            file_name (str): 要删除的文件名
        Returns:
            bool: 删除是否成功
        """
        return self._utils_file.delete_file(file_name)

    def clear_memory_logs(self):
        """
        Desc:
            清除内存中的日志
        """
        return self._utils_file.clear_memory_logs()

    def has_new_error(self):
        """
        Desc:
            检查是否有新的错误日志
        Returns:
            bool: 是否有新错误
        """
        return self._utils_file.has_new_error()

    def clear_new_error_flag(self):
        """
        Desc:
            清除新错误标记
        """
        return self._utils_file.clear_new_error_flag()

    def get_macro_switch_key_name(self):
        """
        Desc:
            获取宏开关按键名称。如果按键名称为 Middle、MSide1 或 MSide2 则返回 False
        Returns:
            str or bool: 按键名称，或 False（表示无有效按键）
        """
        key_name = self._macro.get_key_name()
        if key_name in self._no_key_names:
            return False
        return key_name

    def get_key_name(self):
        """
        Desc:
            获取当前绑定的按键名称
        Returns:
            str: 按键名称
        """
        return self._macro.get_key_name()

    def start_key_listener(self):
        """
        Desc:
            启动按键监听
        Returns:
            dict: {"ok": True}
        """
        self._macro.start_listening_key()
        return {"ok": True}

    def stop_key_listener(self):
        """
        Desc:
            停止按键监听
        Returns:
            dict: {"ok": True}
        """
        self._macro.stop_listening_key()
        return {"ok": True}

    def get_pressed_key(self):
        """
        Desc:
            获取最后按下的按键
        Returns:
            dict: 包含 key 字段，记录最后一次按下的按键
        """
        key = self._macro.get_last_key()
        return {"key": key}

    def set_focus_state(self, focused):
        """
        Desc:
            设置焦点状态
        Args:
            focused (bool): 是否聚焦
        Returns:
            dict: {"ok": True}
        """
        if self._key_mapping:
            self._key_mapping.set_focus_state(focused)
        return {"ok": True}

    def get_mouse_position(self):
        """
        Desc:
            获取鼠标位置
        Returns:
            str: 鼠标坐标，格式为 "x, y"
        """
        x, y = self._macro.get_mouse_position()
        return f'{x}, {y}'

    def get_pixel_color(self):
        """
        Desc:
            获取鼠标所在位置的像素颜色
        Returns:
            str: 颜色值
        """
        return self._macro.get_pixel_color()

    def get_memory_logs(self):
        """
        Desc:
            获取内存中的所有日志
        Returns:
            list: 日志列表
        """
        return self._utils_file.get_memory_logs()

    def get_memory_logs_count(self):
        """
        Desc:
            获取内存日志的总条数
        Returns:
            int: 日志条数
        """
        return self._utils_file.get_memory_logs_count()

    def get_memory_logs_since(self, index):
        """
        Desc:
            获取指定索引之后的内存日志
        Args:
            index (int): 起始索引
        Returns:
            list: 从指定索引开始的日志列表
        """
        return self._utils_file.get_memory_logs_since(index)

    def get_app_info(self):
        """
        Desc:
            获取应用程序信息
        Returns:
            dict: 应用信息字典
        """
        return self._utils_file._load_project_info()

    def minimize(self):
        """
        Desc:
            最小化窗口
        """
        logger.info('Minimize called')
        if self._window:
            try:
                self._window.minimize()
                logger.info('Window minimized successfully')
            except Exception as e:
                logger.error(f'Failed to minimize window: {e}')

    def close(self):
        """
        Desc:
            关闭窗口。根据配置决定是隐藏到系统托盘还是直接销毁
        """
        logger.info('Close called')
        if self._window:
            try:
                config = self._utils_file.load_config_file()
                minimize_to_tray = config.get('minimizeToTray', True)
                if minimize_to_tray:
                    logger.info('Hiding window to tray')
                    self._window.hide()
                else:
                    logger.info('Destroying window')
                    self._window.destroy()
            except Exception as e:
                logger.error(f'Failed to close window: {e}')

    def toggle_maximize(self):
        """
        Desc:
            切换窗口最大化/还原状态
        Returns:
            bool: 最大化返回 True，还原返回 False
        """
        logger.info('Toggle maximize called')
        if self._window:
            try:
                if self._maximized:
                    self._window.restore()
                    self._maximized = False
                    logger.info('Window restored')
                    return False
                self._window.maximize()
                self._maximized = True
                logger.info('Window maximized')
                return True
            except Exception as e:
                logger.error(f'Failed to toggle maximize: {e}')
        return False

    def get_screencast_ratio(self):
        """
        Desc:
            获取投屏的宽高比
        Returns:
            str: 宽高比，格式如 "16:9"
        """
        width, height = self._macro.get_screen_size()
        width, height = int(width), int(height)
        gcd = math.gcd(width, height)
        width_ratio = width // gcd
        height_ratio = height // gcd
        return f'{width_ratio}:{height_ratio}'

    def open_url(self, url: str):
        """
        Desc:
            使用系统默认浏览器打开指定链接
        Args:
            url (str): 要打开的链接地址
        Returns:
            bool: 打开是否成功
        """
        try:
            if sys.platform == 'win32':
                subprocess.run(['start', url], shell=True)
            elif sys.platform == 'darwin':
                subprocess.run(['open', url])
            else:
                subprocess.run(['xdg-open', url])
            return True
        except Exception as e:
            logger.error(f'打开链接失败: {e}')
            return False

    def scrcpy_start(self, serial=None, config=None):
        """
        Desc:
            启动 scrcpy 投屏
        Args:
            serial (str, optional): 设备序列号
            config (dict, optional): 启动配置
        Returns:
            dict: 启动结果
        """
        return self._scrcpy_manager.start(serial, config)

    def scrcpy_stop(self):
        """
        Desc:
            停止 scrcpy 投屏
        Returns:
            dict: 停止结果
        """
        return self._scrcpy_manager.stop()

    def scrcpy_status(self):
        """
        Desc:
            获取 scrcpy 当前状态
        Returns:
            dict: 状态信息
        """
        return self._scrcpy_manager.status()

    def scrcpy_get_ws_port(self):
        """
        Desc:
            获取 scrcpy 的 WebSocket 端口号
        Returns:
            int: 端口号
        """
        return self._scrcpy_manager.get_ws_port()

    def scrcpy_send_touch(self, action, x, y, width, height):
        """
        Desc:
            发送触摸事件到设备
        Args:
            action (int): 触摸动作（按下、移动、释放）
            x (int): 触摸 x 坐标
            y (int): 触摸 y 坐标
            width (int): 触摸区域宽度
            height (int): 触摸区域高度
        Returns:
            dict: 发送结果
        """
        return self._scrcpy_manager.send_touch(action, x, y, width, height)

    def scrcpy_send_keycode(self, keycode, action=0):
        """
        Desc:
            发送按键码到设备
        Args:
            keycode (int): Android 按键码
            action (int): 按键动作，0 按下，1 释放
        Returns:
            dict: 发送结果
        """
        return self._scrcpy_manager.send_keycode(keycode, action)

    def scrcpy_set_clipboard(self, text):
        """
        Desc:
            设置设备剪贴板内容
        Args:
            text (str): 要设置的文本
        Returns:
            dict: 设置结果
        """
        return self._scrcpy_manager.set_clipboard(text)

    def scrcpy_send_text(self, text: str):
        """
        Desc:
            发送文本到设备
        Args:
            text (str): 要发送的文本
        Returns:
            dict: 发送结果
        """
        logger.info(f"Sending text: {text}")
        return self._scrcpy_manager.send_text(text)

    def scrcpy_switch_to_wireless(self):
        """
        Desc:
            切换到无线连接模式
        Returns:
            dict: 切换结果
        """
        return self._scrcpy_manager.switch_to_wireless()

    def scrcpy_discover_usb_serial(self):
        """
        Desc:
            发现 USB 连接的设备序列号
        Returns:
            str or None: 设备序列号，未发现时返回 None
        """
        return self._scrcpy_manager.discover_usb_serial()

    def scrcpy_volume_up(self):
        """
        Desc:
            增大设备音量
        Returns:
            dict: 操作结果
        """
        return self._scrcpy_manager.volume_up()

    def scrcpy_volume_down(self):
        """
        Desc:
            减小设备音量
        Returns:
            dict: 操作结果
        """
        return self._scrcpy_manager.volume_down()

    def scrcpy_back(self):
        """
        Desc:
            模拟设备返回键
        Returns:
            dict: 操作结果
        """
        return self._scrcpy_manager.back()

    def scrcpy_switch_app(self):
        """
        Desc:
            模拟设备切换应用（最近任务）
        Returns:
            dict: 操作结果
        """
        return self._scrcpy_manager.switch_app()

    def scrcpy_home(self):
        """
        Desc:
            模拟设备 Home 键
        Returns:
            dict: 操作结果
        """
        return self._scrcpy_manager.home()

    def get_key_mapping_files(self):
        """
        Desc:
            获取按键映射文件列表
        Returns:
            list: 按键映射文件名列表
        """
        return self._utils_file.get_key_mapping_files()

    def load_key_mapping_file(self, file_name):
        """
        Desc:
            加载指定的按键映射文件
        Args:
            file_name (str): 按键映射文件名
        Returns:
            dict: 按键映射数据
        """
        return self._utils_file.load_key_mapping_file(file_name)

    def save_key_mapping_file(self, file_name, data):
        """
        Desc:
            保存按键映射文件
        Args:
            file_name (str): 文件名
            data (dict): 按键映射数据
        Returns:
            bool: 保存是否成功
        """
        return self._utils_file.save_key_mapping_file(file_name, data)

    def create_key_mapping_file(self):
        """
        Desc:
            创建新的按键映射文件
        Returns:
            str: 创建的文件名
        """
        return self._utils_file.create_key_mapping_file()

    def rename_key_mapping_file(self, old_name, new_name):
        """
        Desc:
            重命名按键映射文件
        Args:
            old_name (str): 原文件名
            new_name (str): 新文件名
        Returns:
            bool: 重命名是否成功
        """
        return self._utils_file.rename_key_mapping_file(old_name, new_name)

    def delete_key_mapping_file(self, file_name):
        """
        Desc:
            删除指定的按键映射文件
        Args:
            file_name (str): 要删除的文件名
        Returns:
            bool: 删除是否成功
        """
        return self._utils_file.delete_key_mapping_file(file_name)

    def apply_key_mapping(self, file_name):
        """
        Desc:
            应用指定的按键映射文件
        Args:
            file_name (str): 按键映射文件名
        Returns:
            dict: 包含操作结果 ok 和可选的错误信息 error
        """
        data = self._utils_file.load_key_mapping_file(file_name)
        if not data:
            return {"ok": False, "error": "failed to load key mapping"}
        self._scrcpy_manager.apply_key_mapping(data)
        if self._key_mapping:
            self._key_mapping.apply(data)
        return {"ok": True}

    def remove_key_mapping(self):
        """
        Desc:
            移除当前应用的按键映射
        Returns:
            dict: {"ok": True}
        """
        self._scrcpy_manager.remove_key_mapping()
        if self._key_mapping:
            self._key_mapping.remove()
        return {"ok": True}

    def scrcpy_send_normalized_touch(self, action, x, y):
        """
        Desc:
            发送归一化坐标的触摸事件（坐标范围为 0~1）
        Args:
            action (int): 触摸动作
            x (float): 归一化 x 坐标（0~1）
            y (float): 归一化 y 坐标（0~1）
        Returns:
            dict: 发送结果
        """
        return self._scrcpy_manager.send_normalized_touch(action, x, y)

    def get_key_mapping_mapped_keys(self):
        """
        Desc:
            获取当前已映射的按键列表
        Returns:
            list: 已映射的按键名称列表
        """
        if self._key_mapping:
            return list(self._key_mapping.get_mapped_keys())
        return []

    def key_mapping_trigger(self, key_name, action):
        """
        Desc:
            触发按键映射操作
        Args:
            key_name (str): 按键名称
            action (int): 按键动作
        Returns:
            dict: 触发结果
        """
        return self._scrcpy_manager.key_mapping_trigger(key_name, action)

    def key_mapping_swipe(self, path_data):
        """
        Desc:
            执行按键映射中的滑动操作
        Args:
            path_data (list): 滑动路径数据
        Returns:
            dict: 滑动结果
        """
        return self._scrcpy_manager.key_mapping_swipe(path_data)

    def get_android_keycode(self, key_name):
        """
        Desc:
            根据按键名称获取对应的 Android 按键码
        Args:
            key_name (str): 按键名称
        Returns:
            int: Android 按键码
        """
        return self._scrcpy_manager.key_mapping_get_android_keycode(key_name)

    def set_screencast_ratio(self, ratio):
        """
        Desc:
            设置投屏宽高比。支持 "reset" 重置、"monitor" 自适应、"16:9" 等模式
        Args:
            ratio (str): 宽高比模式
        Returns:
            dict: 设置结果
        """
        if ratio == "reset":
            return self._scrcpy_manager.reset_screen_ratio()
        if ratio == "monitor":
            w, h = self._macro.get_screen_size()
            w, h = int(w), int(h)
            gcd = math.gcd(w, h)
            wr, hr = w // gcd, h // gcd
            return self._scrcpy_manager.set_screen_ratio(wr, hr)
        if ratio == "16:9":
            return self._scrcpy_manager.set_screen_ratio(16, 9)
        return {"ok": False, "error": f"unknown ratio: {ratio}"}

    def __dir__(self):
        """
        Desc:
            自定义属性列表，用于控制 dir() 和自动补全的返回结果
        Returns:
            list: 可访问的方法名列表
        """
        return [
            'get_app_info', 'minimize', 'close', 'toggle_maximize', 'get_screencast_ratio', 'open_url',
            'get_config_file', 'save_config_file',
            'get_macro_switch_key_name', 'get_key_name', 'get_mouse_position', 'get_pixel_color',
            'get_macro_files', 'load_macrofile', 'save_macrofile',
            'create_new_file', 'rename_file', 'open_folder', 'delete_file',
            'get_memory_logs', 'get_memory_logs_count', 'get_memory_logs_since', 'clear_memory_logs', 'has_new_error', 'clear_new_error_flag',
            'disable_json_editor', 'enable_json_editor', 'save_json_file',
            'set_screencast_ratio',
            'toggle_screencast_fullscreen',
            'scrcpy_start', 'scrcpy_stop', 'scrcpy_status', 'scrcpy_get_ws_port', 'scrcpy_send_touch', 'scrcpy_send_keycode', 'scrcpy_set_clipboard',
            'scrcpy_switch_to_wireless', 'scrcpy_discover_usb_serial',
            'scrcpy_volume_up', 'scrcpy_volume_down', 'scrcpy_back',
            'scrcpy_switch_app', 'scrcpy_home',
            'get_key_mapping_files',
            'load_key_mapping_file',
            'save_key_mapping_file',
            'create_key_mapping_file',
            'rename_key_mapping_file',
            'delete_key_mapping_file',
            'apply_key_mapping',
            'remove_key_mapping',
            'key_mapping_trigger',
            'key_mapping_swipe',
            'get_android_keycode',
            'scrcpy_send_normalized_touch',
            'get_key_mapping_mapped_keys',
            'start_key_listener',
            'set_focus_state',
            'stop_key_listener',
            'get_pressed_key',
            'get_phone_input_state',
        ]
