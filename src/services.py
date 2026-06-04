
class Services:

    def __init__(self):
        # 用 dict 存储所有服务，属性名 -> 服务对象
        super().__setattr__('_services', {})

    def __getattr__(self, name: str) -> any:
        """获取服务"""
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            return self._services[name]
        except KeyError:
            raise AttributeError(
                f"Service '{name}' has not been registered. "
                f"Available: {list(self._services.keys())}"
            ) from None

    def __setattr__(self, name: str, value: any) -> None:
        """设置服务"""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._services[name] = value

    def __delattr__(self, name: str) -> None:
        """删除服务"""
        if name.startswith('_'):
            super().__delattr__(name)
        else:
            del self._services[name]

    def register(self, **services) -> None:
        """批量注册服务"""
        for name, svc in services.items():
            self._services[name] = svc

    def reset(self) -> None:
        """清空所有服务"""
        self._services.clear()

# 全局服务实例 （单例模式）
services = Services()