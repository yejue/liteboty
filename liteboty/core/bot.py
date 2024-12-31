import redis
import logging.config

from pathlib import Path
from typing import Optional

from .config import BotConfig
from .registry import ServiceRegistry
from .exceptions import LiteBotyException


class Bot:
    """LiteBoty机器人主类"""

    def __init__(
            self,
            config_path: str = "config/config.json",
            config: Optional[BotConfig] = None
    ):
        self.config_path = config_path
        self.config = config or BotConfig.load_from_json(Path(config_path))
        self.registry = ServiceRegistry()

        # 设置日志
        logging.config.dictConfig({
            "version": 1,
            "formatters": {
                "default": {
                    "format": self.config.LOGGING.format
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": self.config.LOGGING.level
                }
            },
            "root": {
                "handlers": ["console"],
                "level": self.config.LOGGING.level
            }
        })

        self.logger = logging.getLogger("liteboty.default")

        # 创建Redis客户端
        self.redis_client = redis.Redis(
            host=self.config.REDIS.host,
            port=self.config.REDIS.port
        )

    def _load_services(self) -> None:
        """加载服务"""
        for service_path in self.config.SERVICES:
            try:
                # 检查是否是相对导入（以点号开头）
                if service_path.startswith('.'):
                    # 移除开头的点号，并获取项目根目录
                    import sys
                    project_root = Path.cwd()
                    sys.path.insert(0, str(project_root))

                    try:
                        # 将 .services.hello.service.HelloService 转换为 services.hello.service
                        module_path = service_path.rsplit('.', 1)[0].lstrip('.')
                        class_name = service_path.rsplit('.', 1)[1]

                        module = __import__(module_path, fromlist=[class_name])
                        service_class = getattr(module, class_name)
                    finally:
                        sys.path.pop(0)
                else:
                    # 处理外部包导入
                    module_path, class_name = service_path.rsplit('.', 1)
                    module = __import__(module_path, fromlist=[class_name])
                    service_class = getattr(module, class_name)

                service_config = self.config.get_service_config(class_name)
                service = service_class(config=service_config)
                self.registry.register(service)
                self.logger.info(f"Loaded service: {service_path}")
            except Exception as e:
                self.logger.error(f"Failed to load service {service_path}: {e}")

    def run(self) -> None:
        """运行机器人"""
        self.logger.info("Starting LiteBoty...")
        try:
            self._load_services()
            self.registry.start_all()

            # 等待所有服务
            for service in self.registry.get_all_services():
                if service.main_thread:
                    service.main_thread.join()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        except Exception as e:
            self.logger.error(f"Error: {e}")
            raise LiteBotyException(f"Bot failed: {e}")
