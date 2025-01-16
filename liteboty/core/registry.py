import logging

from typing import Dict, List
from .service import Service
from .exceptions import ServiceError


class ServiceRegistry:
    """服务注册中心"""
    def __init__(self):
        self._services: Dict[str, Service] = {}
        self.logger = logging.getLogger("liteboty_default")

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

    async def start_all(self) -> None:
        """启动所有服务"""
        for service in self._services.values():
            try:
                await service.start()
                self.logger.info(f"Started service: {service.name}")
            except Exception as e:
                self.logger.error(f"Failed to start service {service.name}: {e}")
                raise

    async def stop_all(self) -> None:
        """停止所有服务"""
        for service_name in list(self._services.keys()):
            await self.stop_service(service_name)

    async def stop_service(self, service_name: str) -> None:
        """停止并移除服务"""
        if service := self._services.get(service_name):
            self.logger.info(f"正在停止服务: {service_name}")
            try:
                await service.stop()
                del self._services[service_name]
                self.logger.info(f"服务已停止并移除: {service_name}")
            except Exception as e:
                self.logger.error(f"停止服务 {service_name} 时出错: {e}")
                raise

    async def restart_service(self, service_name: str, config: dict, global_config: dict) -> None:
        """重启服务并更新配置"""
        if service := self._services.get(service_name):
            self.logger.info(f"正在重启服务: {service_name}")
            try:
                await service.stop()
                service.config = config
                service.global_config = global_config
                service._running = True
                await service.start()
                self.logger.info(f"服务已重启: {service_name}")
            except Exception as e:
                self.logger.error(f"重启服务 {service_name} 时出错: {e}")
                raise

    def remove_service(self, service_name: str) -> None:
        """从注册表中移除服务（不停止服务）"""
        if service_name in self._services:
            del self._services[service_name]
            self.logger.info(f"Service removed from registry: {service_name}")

    def has_service(self, service_name: str) -> bool:
        """检查服务是否存在"""
        return service_name in self._services
