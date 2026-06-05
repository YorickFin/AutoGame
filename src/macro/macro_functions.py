import time
import logging
import numpy as np

from ..services import services



logger = logging.getLogger(__name__)


class MacroFunctions:

    @property
    def executor(self):
        return services.macro.executor

    @property
    def macro_window(self):
        return services.macro.macro_window

    @property
    def _ocr(self):
        return services.macro._ocr

    @property
    def match(self):
        return services.macro.match

    def get_screen_size(self):
        import ctypes
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        return screen_width, screen_height

    def continuous(self, data: dict):
        logger.info(f'功能 连击 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            sleep_time = round(1 / (int(data['每秒次数'])), 4)
            down_state_keys = data.get('down_state_keys', [])
            while data['触发键'] in down_state_keys:
                self.executor.execute_macro(data['宏指令'], key_mouse_mode)
                time.sleep(sleep_time)
        except Exception as e:
            logger.error(f'功能 连击 报错信息：{e}')
            raise e

    def fixed_continuous(self, data: dict):
        logger.info(f'功能 固定连击 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            if '连击次数' in data and '连击间隔' in data:
                for _ in range(int(data['连击次数'])):
                    self.executor.execute_macro(data['宏指令'], key_mouse_mode)
                    time.sleep(float(data['连击间隔']))
                if '后置指令' in data:
                    self.executor.execute_macro(data['后置指令'], key_mouse_mode)
            else:
                logger.error(f'功能 固定连击 错误信息：连击次数或连击间隔缺失，当前数据：{data}')
        except Exception as e:
            logger.error(f'功能 固定连击 报错信息：{e}')
            raise e

    def macros(self, data: dict):
        logger.info(f'功能 宏 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            self.executor.execute_macro(data['宏指令'], key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 宏 报错信息：{e}')
            raise e

    def ordered_macros(self, data: dict):
        logger.info(f'功能 有序宏 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            instruct = data['宏指令'].split(',')
            down_state_keys = data.get('down_state_keys', [])
            while data['触发键'] in down_state_keys:
                for macro in instruct:
                    if data['触发键'] not in down_state_keys:
                        return
                    self.executor.execute_macro(macro, key_mouse_mode)
                    if '后置指令' in data:
                        self.executor.execute_macro(data['后置指令'], key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 有序宏 报错信息：{e}')
            raise e

    def follow(self, data: dict, state: bool):
        logger.info(f'功能 跟随 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            instruct = data['宏指令'].split(',')
            if state:
                for macro in instruct:
                    self.executor.execute_macro(f'按下 {macro}', key_mouse_mode)
            else:
                for macro in instruct:
                    self.executor.execute_macro(f'弹起 {macro}', key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 跟随 报错信息：{e}')
            raise e

    def combination(self, data: dict, *args):
        key_mappings = {
            '!辅助': args[0][1],
            '辅助': args[0][0],
        }
        logger.info(f'功能 组合 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            if '分支1' in data and '分支2' in data:
                if key_mappings['辅助'] == data['辅助1']:
                    instruction = data['分支1']
                    for old, new in key_mappings.items():
                        instruction = instruction.replace(old, new)
                    self.executor.execute_macro(instruction, key_mouse_mode)
                else:
                    instruction = data['分支2']
                    for old, new in key_mappings.items():
                        instruction = instruction.replace(old, new)
                    self.executor.execute_macro(instruction, key_mouse_mode)
            else:
                instruction = data['宏指令']
                for old, new in key_mappings.items():
                    instruction = instruction.replace(old, new)
                self.executor.execute_macro(instruction, key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 组合 报错信息：{e}')
            raise e

    def mappings(self, data: dict, *args):
        key_mappings = {
            '!辅助': args[0][1],
            '辅助': args[0][0],
            '!映射': args[0][3],
            '映射': args[0][2],
        }
        logger.info(f'功能 映射 data：{data}')
        try:
            key_mouse_mode = data.get("键鼠模式", 'send')
            instruction = data['宏指令']
            for old, new in key_mappings.items():
                instruction = instruction.replace(old, new)
            self.executor.execute_macro(instruction, key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 映射 报错信息：{e}')
            raise e

    def screenshot(self, data: dict):
        logger.info(f'功能 截图 data：{data}')
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
            logger.error(f'功能 截图 报错信息：{e}')
            raise e

    def track(self, data: dict):
        def hex_to_rgb(hex_color: str):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def verify_rect(rect):
            if len(rect) != 4:
                return False
            x1, y1, x2, y2 = rect
            if x1 >= x2 or y1 >= y2:
                return False
            width = x2 - x1
            height = y2 - y1
            return (width == 1) != (height == 1)

        logger.info(f'功能 追踪 data：{data}')
        try:
            target_color = data.get("目标颜色", None)
            if not target_color:
                logger.error(f'功能 追踪 错误信息：目标颜色缺失，当前数据：{data}')
                return
            target_color = hex_to_rgb(target_color)

            track_color = data.get("追踪颜色", None)
            if not track_color:
                logger.error(f'功能 追踪 错误信息：追踪颜色缺失，当前数据：{data}')
                return
            track_color = hex_to_rgb(track_color)

            rect = tuple(map(int, data.get('匹配范围', "None None None None").strip().split()))
            if 'None' in rect:
                logger.error(f'功能 追踪 错误信息：匹配范围缺失，当前数据：{data}')
                return
            if not verify_rect(rect):
                logger.error(f'功能 追踪 错误信息：匹配范围格式错误，当前数据：{data}')
                return

            key_mouse_mode = data.get("键鼠模式", 'send')
            offset = int(data.get("追踪补偿", 0))

            break_num = 10
            while break_num > 0:
                if self.macro_window:
                    np_colors = self.macro_window.screenshot(rect=rect)
                else:
                    np_colors = self.match.screenshot(rect=rect)

                np_colors = np_colors.reshape(1, -1, 3)
                pixels = np_colors[0]

                target_mask = np.all(pixels == target_color, axis=-1)
                target_indices = np.where(target_mask)[0]
                if len(target_indices) == 0:
                    break_num -= 1
                    logger.info(f'功能 追踪 未找到目标颜色，剩余次数：{break_num}')
                    continue
                target_idx = target_indices[0]
                logger.info(f'功能 追踪 找到目标颜色，索引：{target_idx}')

                track_mask = np.all(pixels == track_color, axis=-1)
                padded = np.pad(track_mask, (1, 1), constant_values=False)
                changes = np.diff(padded.astype(int))
                starts = np.where(changes == 1)[0]
                ends = np.where(changes == -1)[0]
                if len(starts) == 0:
                    break_num -= 1
                    logger.info(f'功能 追踪 未找到追踪颜色，剩余次数：{break_num}')
                    continue
                head = starts[0] + offset
                tail = ends[-1] - offset
                logger.info(f'功能 追踪 找到追踪颜色，头索引：{head}，尾索引：{tail}')

                break_num = 10

                if head >= target_idx and '大于分支' in data:
                    self.executor.execute_macro(data['大于分支'], key_mouse_mode)
                elif tail <= target_idx and '小于分支' in data:
                    self.executor.execute_macro(data['小于分支'], key_mouse_mode)
                else:
                    time.sleep(0.2)

            logger.info('功能 追踪 结束')
            if '后置指令' in data:
                self.executor.execute_macro(data['后置指令'], key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 追踪 报错信息：{e}')
            raise e

    def color_match(self, data: dict):
        logger.info(f'功能 颜色匹配 data：{data}')
        try:
            color_list = data.get("颜色", 'None').strip().split(',')
            if 'None' in color_list:
                logger.error(f'功能 颜色匹配 错误信息：颜色参数错误，预期颜色列表，当前数据：{data}')
                return
            coord_list = data.get("坐标", 'None').strip().split(',')
            if 'None' in coord_list:
                logger.error(f'功能 颜色匹配 错误信息：坐标参数错误，预期坐标列表，当前数据：{data}')
                return
            coord_list = [tuple(map(int, i.split())) for i in coord_list]

            if len(color_list) != len(coord_list):
                logger.error(f'功能 颜色匹配 错误信息：颜色数量与坐标数量不一致，当前数据：{data}')
                return

            key_mouse_mode = data.get("键鼠模式", 'send')
            similarity = float(data.get("相似度", 0.8))
            pattern = data.get("模式", 'all')
            if pattern not in ['all', 'any']:
                logger.error(f'功能 颜色匹配 错误信息：模式参数错误，预期all或any，当前数据：{data}')
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
                self.executor.execute_macro(data['分支Y'], key_mouse_mode)
            elif not flag and '分支N' in data:
                self.executor.execute_macro(data['分支N'], key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 颜色匹配 报错信息：{e}')
            raise e

    def image_match(self, data: dict):
        logger.info(f'功能 图像匹配 data：{data}')
        try:
            target_image_path = data.get("图像名称", None)
            if not target_image_path:
                logger.error(f'功能 图像匹配 错误信息：图像名称缺失，当前数据：{data}')
                return
            if not target_image_path.exists():
                logger.error(f'功能 图像匹配 错误信息：图像文件不存在，当前数据：{data}')
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
                    self.executor.execute_macro(f'移动 {int(x)} {int(y)}', key_mouse_mode)
                self.executor.execute_macro(data["分支Y"], key_mouse_mode)
            elif sim < similarity and '分支N' in data:
                self.executor.execute_macro(data['分支N'], key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 图像匹配 报错信息：{e}')
            raise e

    def text_ocr(self, data: dict):
        logger.info(f'功能 文字识别 data：{data}')
        try:
            target_text = data.get("目标文本", 'None')
            if 'None' in target_text:
                logger.error(f'功能 文字识别 错误信息：目标文本参数错误，预期字符串，当前数据：{data}')
                return

            pattern = data.get("模式", 'all')
            if pattern not in ['all', 'any']:
                logger.error(f'功能 文字识别 错误信息：模式参数错误，预期all或any，当前数据：{data}')
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

            ocr_result = self._ocr(target_image)

            x, y, flag = 0, 0, False
            for line in ocr_result:
                if pattern == 'all':
                    if line['text'] == target_text:
                        dx, dy = line['center']
                        x, y = dx + int(rect[0]), dy + int(rect[1])
                        flag = True
                        break
                elif pattern == 'any':
                    for char in line['text']:
                        if char in target_text:
                            dx, dy = line['center']
                            x, y = dx + int(rect[0]), dy + int(rect[1])
                            flag = True
                            break

            if flag and '分支Y' in data:
                if data.get('定位目标') == '是':
                    self.executor.execute_macro(f'移动 {int(x)} {int(y)}', key_mouse_mode)
                self.executor.execute_macro(data["分支Y"], key_mouse_mode)
            elif not flag and '分支N' in data:
                self.executor.execute_macro(data['分支N'], key_mouse_mode)
        except Exception as e:
            logger.error(f'功能 文字识别 报错信息：{e}')
            raise e