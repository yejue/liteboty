import logging

from typing import Dict, List
from .service import Service
from .exceptions import ServiceError


class ServiceRegistry:
    """服务注册中心"""
    def __init__(self):
        self._services: Dict[str, Service] = {}
        self.logger = logging.getLogger("liteboty.default")

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

    def stop_service(self, service_name: str) -> None:
        """停止并移除服务"""
        if service := self._services.get(service_name):
            self.logger.info(f"正在停止服务: {service_name}")
            service.stop()
            del self._services[service_name]
            self.logger.info(f"服务已停止并移除: {service_name}")

    def restart_service(self, service_name: str, new_config: dict) -> None:
        """重启服务并更新配置"""
        if service := self._services.get(service_name):
            self.logger.info(f"正在重启服务: {service_name}")
            service.stop()
            # 更新配置并重启
            service.config = new_config
            service._running = True
            service._stopped.clear()
            service.start()
            self.logger.info(f"服务已重启: {service_name}")
