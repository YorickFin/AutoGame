from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.api import Api
    from src.key_mapping import KeyMappingExecutor
    from src.macro import Macro
    from src.scrcpy import ScrcpyManager
    from src.utils.utils_file import utils_file
    from src.utils.utils_path import utils_path


class Services:
    api: 'Api'
    macro: 'Macro'
    scrcpy: 'ScrcpyManager'
    key_mapping_executor: 'KeyMappingExecutor'
    utils_file: 'utils_file'
    utils_path: 'utils_path'
    ocr: Callable[..., Any]
    position: tuple[int, int]
    window: Any

    def register(self, **services: Any) -> None: ...
    def reset(self) -> None: ...


services: Services
