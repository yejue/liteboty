import sys
import importlib
import time
import asyncio
import logging.config
import json

from pathlib import Path
from typing import Optional, Set, List, Tuple

import redis.asyncio as aioredis

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .config import BotConfig
from .registry import ServiceRegistry
from .exceptions import LiteBotyException
from .utils import get_service_name_from_path


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

        # Add Redis client for service list management
        self.redis_client = None
        self._init_redis()

        # 设置日志配置
        _setup_logging(self.config)
        self.logger = logging.getLogger("liteboty_default")

        # 添加配置文件监控
        self.observer = Observer()
        handler = ConfigFileHandler(self)
        self.observer.schedule(handler, path=str(Path(config_path).parent.resolve()), recursive=False)

        # service list refresh & TTL
        self.service_update_interval = getattr(self.config, "SERVICE_LIST_UPDATE_INTERVAL", 15)
        self.service_ttl_seconds = max(
            getattr(self.config, "SERVICE_LIST_TTL_SECONDS", self.service_update_interval * 2),
            30
        )
        self._service_update_task = None

    def _init_redis(self) -> None:
        """Initialize Redis connection for service list management"""
        try:
            redis_config = self.config.REDIS.model_dump()
            self.redis_client = aioredis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                password=redis_config.get('password'),
                db=redis_config.get('db', 0),
                socket_timeout=redis_config.get('socket_timeout'),
                socket_connect_timeout=redis_config.get('socket_connect_timeout'),
                decode_responses=redis_config.get('decode_responses', False)
            )
        except Exception as e:
            self.logger.warning(f"Failed to initialize Redis client: {e}")
            self.redis_client = None

    async def _update_service_list_in_redis(self, action: str = "update") -> None:
        """Update service list in Redis

        Args:
            action: "update" for full update, "remove_all" for cleanup
        """
        if not self.redis_client:
            return

        try:
            service_key = "liteboty:services"

            if action == "remove_all":
                await self.redis_client.delete(service_key)
                self.logger.info("Cleared liteboty service list from Redis")
                return

            # Get all services from registry
            services = self.registry.get_all_services()
            service_list = []

            for service in services:
                service_info = {
                    "name": service.name,
                    "status": "running" if service._running else "stopped",
                    "start_time": getattr(service, '_start_time', None),
                    "uptime": time.time() - getattr(service, '_start_time', time.time()),
                    "last_update": time.time()
                }
                service_list.append(service_info)

            # Store as JSON string in Redis
            await self.redis_client.set(service_key, json.dumps(service_list))
            # short TTL so it expires if bot crashes; kept alive by periodic refresh
            await self.redis_client.expire(service_key, self.service_ttl_seconds)
            self.logger.debug(f"Updated liteboty service list in Redis: {len(service_list)} services")

        except Exception as e:
            self.logger.error(f"Failed to update service list in Redis: {e}")

    def set_reload_config(self):
        self.need_to_reload = True

    async def _check_reload(self):
        while self._running:
            # self.logger.info("checking reload")
            if self.need_to_reload:
                await self.reload_config()
                self.need_to_reload = False
            await asyncio.sleep(0.5)

    async def _service_list_updater(self) -> None:
        """Periodically refresh service list in Redis to keep TTL alive"""
        while self._running:
            try:
                await self._update_service_list_in_redis()
            except Exception as e:
                self.logger.error(f"Service list updater error: {e}")
            await asyncio.sleep(self.service_update_interval)

    @staticmethod
    def _get_service_changes(old_config: BotConfig, new_config: BotConfig) -> Tuple[
        Set[str], Set[str], List[str]]:
        """获取服务变更情况

        Args:
            old_config: 旧配置
            new_config: 新配置

        Returns:
            Tuple[Set[str], Set[str], List[str]]: 需要停止的服务、需要启动的服务、配置变更的服务
        """
        # 获取旧配置中启用的服务
        old_services = set(old_config.get_enabled_services())
        # 获取新配置中启用的服务
        new_services = set(new_config.get_enabled_services())

        # 计算需要停止和启动的服务
        services_to_stop = old_services - new_services
        services_to_start = new_services - old_services

        # 获取配置变更的服务
        changed_services = []

        # 遍历新配置中的服务，检查配置是否变更
        for service_path in old_services.intersection(new_services):
            service_name = get_service_name_from_path(service_path)
            old_service_config = old_config.get_service_config(service_name)
            new_service_config = new_config.get_service_config(service_name)

            if old_service_config != new_service_config:
                changed_services.append(service_path)

        return services_to_stop, services_to_start, changed_services

    async def reload_config(self) -> None:
        """重新加载配置并更新服务"""
        self.logger.info("检测到配置文件变更，正在重新加载...")
        try:
            new_config = BotConfig.load_from_json(Path(self.config_path))

            # 获取服务变更情况
            services_to_stop, services_to_start, changed_services = self._get_service_changes(self.config, new_config)

            self.logger.info(f"Services to stop: {services_to_stop}")
            self.logger.info(f"Services to start: {services_to_start}")
            self.logger.info(f"Services to restart: {changed_services}")

            # 停止需要停止的服务
            for service_path in services_to_stop:
                try:
                    service_name = get_service_name_from_path(service_path)
                    await self.registry.stop_service(service_name)
                    self.logger.info(f"服务已停止: {service_name}")
                except Exception as e:
                    self.logger.error(f"关闭服务 {service_path} 失败: {e}")

            # 启动新增的服务（按优先级排序）
            sorted_services_to_start = sorted(
                services_to_start,
                key=lambda s: new_config.SERVICE_PRIORITIES.get(s, 100)
            )

            for service_path in sorted_services_to_start:
                try:
                    await self._load_service(service_path)
                    service_name = get_service_name_from_path(service_path)
                    if service := self.registry.get_service(service_name):
                        await service.start()
                        self.logger.info(f"新服务已启动: {service_name}")
                except Exception as e:
                    self.logger.error(f"启动服务 {service_path} 失败: {e}")

            # 重启配置变更的服务
            for service_path in changed_services:
                try:
                    service_name = get_service_name_from_path(service_path)
                    self.logger.debug(f"changed service: {service_name}")
                    new_service_config = new_config.get_service_config(service_name)
                    self.logger.debug(f"new_servie_config: {new_service_config}")
                    await self.registry.restart_service(service_name, new_service_config, new_config.model_dump())
                    self.logger.info(f"服务已重启: {service_name}")
                except Exception as e:
                    self.logger.error(f"重启服务 {service_path} 失败: {e}")

            # 更新配置
            self.config = new_config
            self.logger.info("配置重新加载完成")

            # Update service list in Redis after reload
            await self._update_service_list_in_redis()

        except Exception as e:
            self.logger.error(f"重新加载配置失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    async def _load_service(self, service_path: str) -> None:
        """加载单个服务，支持本地包和标准包，自动注册到 registry"""
        try:
            # 1. 导入包，获取 service_entry
            if service_path.startswith('.'):
                package_name = service_path.lstrip('.')
                sys.path.insert(0, str(Path.cwd()))
                try:
                    module = importlib.import_module(package_name)
                finally:
                    sys.path.pop(0)
            else:
                module = importlib.import_module(service_path)

            if not hasattr(module, "service_entry"):
                raise ImportError(f"Service 包 {service_path} 必须在 __init__.py 暴露 service_entry")
            service_class = getattr(module, "service_entry")

            # 2. 用 service_name（包名）查 config
            service_name = get_service_name_from_path(service_path)
            service_config = self.config.get_service_config(service_name)

            # 3. 实例化并注册
            service = service_class(config=service_config, global_config=self.config.model_dump())
            self.registry.register(service)
            self.logger.info(f"Loaded service: {service_path}")

        except Exception as e:
            self.logger.error(f"Failed to load service {service_path}: {e}")
            raise

    async def _load_services(self) -> None:
        """加载所有启用的服务"""
        # 获取按优先级排序后的服务列表
        sorted_services = self.config.get_sorted_services()
        self.logger.info(f"Loading services in order: {sorted_services}")

        for service_path in sorted_services:
            try:
                await self._load_service(service_path)
            except Exception as e:
                self.logger.error(f"Failed to load service {service_path}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                continue

        # Update service list in Redis after loading all services
        await self._update_service_list_in_redis()

    async def run(self) -> None:
        """运行机器人"""
        self.logger.info("Starting LiteBoty...")
        check_reload_loop = None
        try:
            await self._load_services()
            self.observer.start()
            await self.registry.start_all()

            # Update service list after all services started
            await self._update_service_list_in_redis()

            # start periodic refresh to keep 'liteboty:services' fresh with short TTL
            self._service_update_task = asyncio.create_task(self._service_list_updater())

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

            # Clean up service list from Redis
            await self._update_service_list_in_redis(action="remove_all")

            if self.redis_client:
                await self.redis_client.aclose()

            if check_reload_loop is not None:
                check_reload_loop.cancel()
                try:
                    await check_reload_loop
                except asyncio.CancelledError:
                    pass

    async def stop(self) -> None:
        """停止机器人"""
        self._running = False
        if self._service_update_task is not None:
            self._service_update_task.cancel()
            try:
                await self._service_update_task
            except asyncio.CancelledError:
                pass
        await self.registry.stop_all()
        await self._update_service_list_in_redis(action="remove_all")

    def get_loop(self):
        return self._loop
