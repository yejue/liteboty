from typing import Dict, List
from .service import Service
from .exceptions import ServiceError


class ServiceRegistry:
    """服务注册中心"""
    def __init__(self):
        self._services: Dict[str, Service] = {}

    def register(self, service: Service) -> None:
        """注册服务"""
        if service.name in self._services:
            raise ServiceError(f"Service {service.name} already registered")
        self._services[service.name] = service

    def get_service(self, name: str) -> Service:
        """获取服务"""
        return self._services.get(name)

    def get_all_services(self) -> List[Service]:
        """获取所有服务"""
        return list(self._services.values())

    def start_all(self) -> None:
        """启动所有服务"""
        for service in self._services.values():
            service.start()