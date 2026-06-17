from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.api import Api
    from src.key_mapping import KeyMapping
    from src.key_mapping.camera_controller import CameraController
    from src.macro import Macro
    from src.scrcpy import ScrcpyManager, WsStreamServer
    from src.utils import UtilsFile, utils_path


class Services:
    api: 'Api'
    macro: 'Macro'
    scrcpy_manager: 'ScrcpyManager'
    ws_stream_server: 'WsStreamServer'
    key_mapping: 'KeyMapping'
    camera_controller: 'CameraController'
    utils_file: 'UtilsFile'
    utils_path: 'utils_path'
    ocr: Callable[..., Any]
    window: Any

    def register(self, **services: Any) -> None: ...
    def reset(self) -> None: ...


services: Services
