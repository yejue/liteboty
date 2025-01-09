import logging
import asyncio

import redis.asyncio as aioredis

from typing import Any, Dict, Optional

from .exceptions import ServiceError


class Service:
    def __init__(
            self,
            name: str,
            config: Optional[Dict[str, Any]] = None,
            global_config: Optional[Dict[str, Any]] = None,
            need_redis: bool = True,  # 控制是否需要 Redis
    ):
        self.name = name
        self.config = config or {}
        self.global_config = global_config or {}
        self.logger = logging.getLogger(f"liteboty.default")

        self.redis_client = None
        self.subscriber = None
        self._subscriptions = {}  # 存储订阅信息

        # 生命周期控制相关
        self._running = True
        self._task = None

        if need_redis:
            self._init_redis()

    def _init_redis(self) -> None:
        """初始化 Redis 异步连接"""
        redis_config = self.config.get('REDIS', self.global_config.get('REDIS', {}))

        self.redis_client = aioredis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            password=redis_config.get('password'),
            db=redis_config.get('db', 0),
            socket_timeout=redis_config.get('socket_timeout'),
            socket_connect_timeout=redis_config.get('socket_connect_timeout'),
            decode_responses=redis_config.get('decode_responses', False)
        )

        self.subscriber = self.redis_client.pubsub()
        self.logger.info(f"Service {self.name} created Redis client")

    async def _reconnect(self, max_retries: int = None, initial_backoff: float = 1.0) -> bool:
        """重连 Redis

        Args:
            max_retries: 最大重试次数，None 表示无限重试
            initial_backoff: 初始退避时间（秒）

        Returns:
            bool: 重连是否成功
        """
        backoff = initial_backoff
        retries = 0

        while self._running:
            try:
                self._init_redis()
                # 重新订阅所有频道
                for channel, callback in self._subscriptions.items():
                    await self.subscriber.subscribe(**{channel: callback})
                self.logger.info("Successfully reconnected to Redis")
                return True
            except aioredis.ConnectionError as e:
                retries += 1
                if max_retries is not None and retries >= max_retries:
                    self.logger.error(f"Failed to reconnect after {retries} attempts")
                    return False

                self.logger.warning(f"Reconnection failed, retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)  # 指数退避，最大 30 秒
            except Exception as e:
                self.logger.error(f"Unexpected error during reconnection: {e}")
                return False

    async def subscribe(self, channel: str, callback: callable) -> None:
        """订阅消息并处理重连

        Args:
            channel: 订阅的频道
            callback: 消息处理回调函数
        """
        if not self.subscriber:
            raise ServiceError("Redis subscriber not initialized")

        # 保存订阅信息用于重连
        self._subscriptions[channel] = callback

        # 订阅频道
        await self.subscriber.subscribe(**{channel: callback})

        while self._running:
            try:
                message = await self.subscriber.get_message(timeout=0.1)
                if message and message['type'] == 'message':
                    try:
                        await callback(message['data'])
                    except Exception as e:
                        self.logger.error(f"Error in callback: {e}")
            except aioredis.ConnectionError as e:
                self.logger.error(f"Redis connection lost: {e}")
                if not await self._reconnect():
                    break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(1)

    async def start(self):
        """启动任务"""
        self._task = asyncio.create_task(self.run())

    async def run(self):
        """ 应用的主逻辑，需要在子类中实现 """
        raise NotImplementedError("需要在子类中覆盖该类")

    async def unsubscribe(self, channel: str) -> None:
        """取消订阅"""
        if channel in self._subscriptions:
            await self.subscriber.unsubscribe(channel)
            del self._subscriptions[channel]

    async def stop(self):
        """停止服务"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self.cleanup()

    async def cleanup(self) -> None:
        """子类可以覆盖此方法以实现自定义清理逻辑"""
        pass

    async def publish_message(self, topic, message):
        """ 发送消息到 Redis 的指定 topic """
        try:
            await self.redis_client.publish(topic, message)
        except aioredis.ConnectionError:
            self.logger.error("Redis connection lost while publishing message")
            if await self._reconnect():
                await self.redis_client.publish(topic, message)
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
