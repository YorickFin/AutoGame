from .backend_api import BackendApi
from .frontend_api import FrontendApi

class Api(BackendApi, FrontendApi):
    def __init__(self):
        BackendApi.__init__(self)
        FrontendApi.__init__(self)

__all__ = [
    'Api'
]
