from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LogConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379


class BotConfig(BaseSettings):
    """机器人配置"""
    REDIS: RedisConfig = Field(default_factory=RedisConfig)
    LOGGING: LogConfig = Field(default_factory=LogConfig)
    SERVICES: list[str] = []
    SERVICE_CONFIG: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def load_from_json(cls, path: Path) -> 'BotConfig':
        """从JSON文件加载配置"""
        try:
            return cls.parse_file(path)
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}")

    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """获取服务配置"""
        return self.SERVICE_CONFIG.get(service_name, {})
