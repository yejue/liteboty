import json
import time
from pathlib import Path
import random
from functools import wraps
from typing import Any, Dict, Optional, List, Callable
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
    REDIS: RedisConfig = Field(default_factory=RedisConfig)
    LOGGING: LogConfig = Field(default_factory=LogConfig)
    SERVICES: List[str] = []
    SERVICE_CONFIG: Dict[str, Dict[str, Any]] = {}
    CONFIG_MAP: Dict[str, str] = {}

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

