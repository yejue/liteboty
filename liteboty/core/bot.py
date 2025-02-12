import time
import asyncio
import logging.config

from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .config import BotConfig
from .registry import ServiceRegistry
from .exceptions import LiteBotyException


class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, bot):
        self.bot = bot
        self.last_modified = 0
        # self._reload_lock = asyncio.Lock()

    def on_modified(self, event):
        if event.src_path == str(self.bot.config_path):
            # 防止重复触发
            current_time = time.time()
            if current_time - self.last_modified < 1:
                return
            self.last_modified = current_time
            # logging.getLogger("liteboty_default").info("File modified")
            self.bot.set_reload_config()

def _setup_logging(config: BotConfig) -> None:
    """设置日志配置
    Args:
        config: Bot配置对象
    """
    # 基础日志配置
    log_config = {
        "version": 1,
        "formatters": {
            "default": {
                "format": config.LOGGING.format
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": config.LOGGING.level
            }
        },
        "loggers": {
            "liteboty_default": {
                "handlers": ["console"],
                "level": config.LOGGING.level
            }
        }
    }

    # 如果配置了日志目录，添加文件处理器
    if hasattr(config.LOGGING, 'log_dir') and config.LOGGING.log_dir:
        log_dir = Path(config.LOGGING.log_dir)
        print(f"Logging directory: {log_dir}")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "liteboty.log"

        log_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_file),
            "formatter": "default",
            "level": config.LOGGING.level,
            "maxBytes": config.LOGGING.max_bytes,
            "backupCount": config.LOGGING.backup_count
        }
        log_config["loggers"]["liteboty_default"]["handlers"].append("file")

    logging.config.dictConfig(log_config)


class Bot:
    """LiteBoty机器人主类"""

    def __init__(
            self,
            config_path: str = r"config/config.json",
            config: Optional[BotConfig] = None
    ):

        # 记录 Bot 的事件循环
        self._loop = asyncio.get_event_loop()
        self.config_path = Path(config_path).resolve()
        self.config = config or BotConfig.load_from_json(Path(config_path))
        self.registry = ServiceRegistry()
        self._running = True

        self.need_to_reload = False

        # 设置日志配置
        _setup_logging(self.config)
        self.logger = logging.getLogger("liteboty_default")

        # 添加配置文件监控
        self.observer = Observer()
        handler = ConfigFileHandler(self)
        self.observer.schedule(handler, path=str(Path(config_path).parent.resolve()), recursive=False)

    def set_reload_config(self):
        self.need_to_reload = True

    async def _check_reload(self):
        while self._running:
            # self.logger.info("checking reload")
            if self.need_to_reload:
                await self.reload_config()
                self.need_to_reload = False
            await asyncio.sleep(0.5)

    @staticmethod
    def compare_service_configs_with_map(old_config, new_config) -> list:
        changed_services = []

        # 获取 SERVICE_CONFIG 和 CONFIG_MAP 部分
        old_service_config = old_config.get("SERVICE_CONFIG", {})
        new_service_config = new_config.get("SERVICE_CONFIG", {})
        config_map = new_config.get("CONFIG_MAP", {})

        # 遍历SERVICE_CONFIG中的每个服务
        for service, config in old_service_config.items():
            # 如果在 new_config 中没有该服务，或者配置内容不同，认为服务发生了变化
            if service not in new_service_config or old_service_config[service] != new_service_config[service]:
                changed_services.append(service)

        # 使用CONFIG_MAP来找到实际的服务名称
        mapped_services = []
        for service in changed_services:
            if service in config_map:
                mapped_services.append(config_map[service])

        return mapped_services

    async def reload_config(self) -> None:
        """重新加载配置并更新服务"""
        self.logger.info("检测到配置文件变更，正在重新加载...")
        try:
            new_config = BotConfig.load_from_json(Path(self.config_path))
            old_services = set(self.config.SERVICES)
            new_services = set(new_config.SERVICES)

            # 处理被移除的服务
            self.logger.info("Services to offload: {}".format(old_services - new_services))
            self.logger.info("Services to onload: {}".format(new_services - old_services))

            # TODO: 应该有一个更好的配置结构，以优化 module_path 和 service_config 的映射
            # TODO: 当前加载服务使用了路径或模块名，而在注册中心注册时用的是 name，这样的结构很难以对这三者进行映射关联

            for service_path in old_services - new_services:
                try:
                    service_name = service_path.rsplit('.', 1)[1]
                    await self.registry.stop_service(service_name)
                except Exception as e:
                    self.logger.error(f"关闭服务 {service_path} 失败: {e}")

            # 处理新增的服务
            for service_path in new_services - old_services:
                try:
                    await self._load_service(service_path)
                    service_name = service_path.split('.')[-1]
                    if service := self.registry.get_service(service_name):
                        await service.start()
                        self.logger.info(f"新服务已启动: {service_name}")
                except Exception as e:
                    self.logger.error(f"启动服务 {service_path} 失败: {e}")
                
            # 处理配置变更的服务
            changed_services = self.compare_service_configs_with_map(self.config.dict(), new_config.dict())
            self.logger.info(f"Services to change config：{changed_services}")

            for service_path in changed_services:
                try:
                    service_name = service_path.rsplit('.', 1)[1]
                    old_service_config = self.config.get_service_config(service_name)
                    new_service_config = new_config.get_service_config(service_name)

                    if old_service_config != new_service_config:
                        await self.registry.restart_service(service_name, new_service_config, new_config)
                except Exception as e:
                    self.logger.error(f"重启服务 {service_path} 失败: {e}")

            self.config = new_config
            self.logger.info("配置重新加载完成")

        except Exception as e:
            self.logger.error(f"重新加载配置失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    async def _load_service(self, service_path: str) -> None:
        """加载单个服务"""
        try:
            # 检查是否是相对导入
            if service_path.startswith('.'):
                import sys
                project_root = Path.cwd()
                sys.path.insert(0, str(project_root))

                try:
                    module_path = service_path.rsplit('.', 1)[0].lstrip('.')
                    class_name = service_path.rsplit('.', 1)[1]
                    module = __import__(module_path, fromlist=[class_name])
                    service_class = getattr(module, class_name)
                finally:
                    sys.path.pop(0)
            else:
                module_path, class_name = service_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                service_class = getattr(module, class_name)

            service_config = self.config.get_service_config(class_name)
            service = service_class(config=service_config, global_config=self.config.dict())
            self.registry.register(service)
            self.logger.info(f"Loaded service: {service_path}")

        except Exception as e:
            self.logger.error(f"Failed to load service {service_path}: {e}")
            raise

    async def _load_services(self) -> None:
        """加载所有服务"""
        for service_path in self.config.SERVICES:
            try:
                await self._load_service(service_path)
            except Exception as e:
                self.logger.error(f"Failed to load service {service_path}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                continue

    async def run(self) -> None:
        """运行机器人"""
        self.logger.info("Starting LiteBoty...")
        check_reload_loop = None
        try:
            await self._load_services()
            self.observer.start()
            await self.registry.start_all()
            check_reload_loop = asyncio.create_task(self._check_reload())

            # 保持运行直到收到停止信号
            while self._running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            self.logger.info("Received shutdown signal...")
        except KeyboardInterrupt:
            self.logger.info(f"KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Error: {e}")
            raise LiteBotyException(f"Bot failed: {e}")
        finally:
            self.logger.info("Shutting down...")
            self.observer.stop()
            self.observer.join()
            await self.registry.stop_all()
            if check_reload_loop is not None:
                await check_reload_loop

    async def stop(self) -> None:
        """停止机器人"""
        self._running = False
        await self.registry.stop_all()

    def get_loop(self):
        return self._loop
