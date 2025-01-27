import json

from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from liteboty.core.exceptions import ConfigError


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


class BotConfig(BaseSettings):
    """机器人配置"""
    REDIS: RedisConfig = Field(default_factory=RedisConfig)
    LOGGING: LogConfig = Field(default_factory=LogConfig)
    SERVICES: List[str] = []
    SERVICE_CONFIG: Dict[str, Dict[str, Any]] = {}
    CONFIG_MAP: Dict[str, str] = {}

    @classmethod
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
