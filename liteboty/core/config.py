import json
import time
import random

from pathlib import Path
from functools import wraps
from typing import Any, Dict, Optional, List, Callable, Union

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings

from liteboty.core.exceptions import ConfigError
from .utils import get_service_name_from_path


class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    socket_timeout: Optional[float] = None
    socket_connect_timeout: Optional[float] = None
    decode_responses: bool = False


class LogConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - File: %(filename)s - Line: %(lineno)s - %(message)s",
    log_dir: Optional[str] = None
    max_bytes: int = 10485760
    backup_count: int = 5


class ServiceItem(BaseModel):
    """服务项配置"""
    enabled: bool = True
    priority: int = 100  # 服务启动优先级，数字越小优先级越高
    config: Dict[str, Any] = {}


def exponential_backoff(
        max_tries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 32.0,
        jitter: bool = True
) -> Callable:
    """
    指数退避重试装饰器

    参数:
        max_tries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        jitter: 是否启用随机抖动
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            tries = 0

            while tries < max_tries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    tries += 1

                    # 如果达到最大尝试次数，重新抛出异常
                    if tries >= max_tries:
                        raise ConfigError(f"配置加载失败：{str(e)}")

                    # 计算延迟时间
                    current_delay = min(delay * random.uniform(0.5, 1.5) if jitter else delay, max_delay)
                    print(f"配置加载尝试 {tries}/{max_tries} 失败，将在 {current_delay:.1f} 秒后重试")

                    # 等待并增加下一次延迟
                    time.sleep(current_delay)
                    delay *= 2

        return wrapper

    return decorator


class BotConfig(BaseSettings):
    """机器人配置"""
    version: str = "1.0"
    REDIS: RedisConfig = Field(default_factory=RedisConfig)
    LOGGING: LogConfig = Field(default_factory=LogConfig)

    # 支持新旧两种配置格式
    SERVICES: Union[List[str], Dict[str, ServiceItem]] = Field(default_factory=list)
    SERVICE_CONFIG: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    CONFIG_MAP: Dict[str, str] = Field(default_factory=dict)

    # 服务优先级映射
    SERVICE_PRIORITIES: Dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def handle_config_format(cls, values):
        """处理新旧两种配置格式"""
        version = values.get("version", "1.0")

        # 旧版本格式 (version 1.0)
        if version == "1.0":
            return values

        # 新版本格式 (version 2.0)
        if version == "2.0" and isinstance(values.get("SERVICES"), dict):
            services_dict = values["SERVICES"]

            # 转换为旧格式兼容
            service_list = []
            service_config = {}
            config_map = {}
            service_priorities = {}

            for service_path, service_item in services_dict.items():
                if isinstance(service_item, dict) and service_item.get("enabled", True):
                    service_list.append(service_path)

                # 提取服务名称
                service_name = get_service_name_from_path(service_path)

                # 处理配置
                if isinstance(service_item, dict):
                    service_config[service_name] = service_item.get("config", {})

                    # 处理优先级
                    priority = service_item.get("priority", 100)
                    service_priorities[service_path] = priority

                config_map[service_name] = service_path

            # 更新配置
            values["SERVICES"] = service_list
            values["SERVICE_CONFIG"] = service_config
            values["CONFIG_MAP"] = config_map
            values["SERVICE_PRIORITIES"] = service_priorities

        return values

    @classmethod
    @exponential_backoff(max_tries=3, initial_delay=1.0, max_delay=32.0)
    def load_from_json(cls, path: Path) -> 'BotConfig':
        """从JSON文件加载配置"""
        try:
            with open(path, "r", encoding="utf8") as f:
                json_data = json.load(f)
            return cls.model_validate(json_data)
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}")

    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """获取服务配置"""
        return self.SERVICE_CONFIG.get(service_name, {})

    def get_enabled_services(self) -> List[str]:
        """获取启用的服务列表"""
        if isinstance(self.SERVICES, list):
            return self.SERVICES

        # 如果是字典格式，过滤出启用的服务
        return [
            service_path
            for service_path, service_item in self.SERVICES.items()
            if isinstance(service_item, dict) and service_item.get("enabled", True)
        ]

    def get_sorted_services(self) -> List[str]:
        """获取按优先级排序的服务列表"""
        services = self.get_enabled_services()

        # 如果是旧版本格式或者没有设置优先级，直接返回
        if self.version == "1.0" or not self.SERVICE_PRIORITIES:
            return services

        # 按优先级排序（数字越小优先级越高）
        return sorted(services, key=lambda s: self.SERVICE_PRIORITIES.get(s, 100))
