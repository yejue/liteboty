import logging
import asyncio

import redis.asyncio as aioredis

from typing import Any, Dict, Optional
from .message import Message, MessageType
from .utils import TimerLoop
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
        self.logger = logging.getLogger(f"liteboty_default")

        self.redis_client = None
        self.subscriber = None
        self._subscriptions = {}  # 存储订阅信息
        self._timers = {}

        # 生命周期控制相关
        self._running = True
        self._tasks = []

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

    def add_subscription(self, channel: str, callback: callable):
        """ 订阅 Redis 的指定 topic 并设置回调
         
        Args:
            channel: 订阅的频道
            callback: 消息处理回调函数
         """
        if channel not in self._subscriptions:
            self._subscriptions[channel] = callback
    
    def add_timer(self, timer_name, interval, callback, count=None):
        """ 添加定时器 """
        if timer_name in self._timers:
            raise ServiceError(f"Timer {timer_name} already exists")

        self._timers[timer_name] = TimerLoop(timer_name, interval, callback, count=count)

    async def start(self) -> None:
        """订阅消息并处理重连
        """
        self._tasks = [
            asyncio.create_task(self._timers[timer_name].run())
            for timer_name in self._timers
        ]

        if self.subscriber:
            await self.subscriber.subscribe(**self._subscriptions)
            if len(self._subscriptions) > 0:
                self._tasks.append(asyncio.create_task(self.subscriber.run()))

    async def start_subscriber(self) -> None:
        """开启订阅"""
        await self.subscriber.subscribe(**self._subscriptions)
        if len(self._subscriptions) > 0:
            self._tasks.append(asyncio.create_task(self.subscriber.run()))

    async def restart_subscriber(self, max_retries: int = 3, initial_backoff: float = 1.0) -> bool:
        """手动重启 Redis 订阅连接

        Args:
            max_retries: 最大重试次数，None 表示无限重试
            initial_backoff: 初始退避时间（秒）

        Returns:
            bool: 重启是否成功
        """
        self.logger.info("Restarting Redis subscriber...")
        try:
            # 关闭现有订阅连接
            if self.subscriber:
                await self.subscriber.unsubscribe(*self._subscriptions.keys())
                await self.subscriber.aclose()

            # 重建 Redis 连接和订阅
            await self._reconnect(max_retries=max_retries, initial_backoff=initial_backoff)
            self.logger.info("Redis subscriber restarted successfully.")
            return True
        except Exception as e:
            self.logger.error(f"Error restarting Redis subscriber: {e}")
            return False

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

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print("Except  asyncio.CancelledError")
                pass
        await self.cleanup()
        await self.subscriber.aclose()
        await self.redis_client.aclose()

    async def cleanup(self) -> None:
        """子类可以覆盖此方法以实现自定义清理逻辑"""
        pass

    async def publish(
            self,
            channel: str,
            data: Any,
            msg_type: MessageType,
            metadata: Optional[Dict] = None,
    ) -> None:
        """发布数据为消息

        Args:
            channel: 发布通道
            data: 要发布的数据
            msg_type: 消息类型
            metadata: 元数据字典
        """
        try:
            if metadata is None:
                metadata = {}

            message = Message(data, msg_type, metadata)
            await self.publish_message(channel, message)
        except Exception as e:
            self.logger.error(f"Error publishing data: {e}")
            raise

    async def publish_message(self, channel: str, message: Message) -> None:
        """发布自定义消息

        Args:
            channel: 发布通道
            message: Message 对象

        Example:
            custom_msg = Message(
                data=my_data,
                msg_type=MessageType.JSON,
                metadata={
                    'custom_field': 'value',
                    'timestamp': time.time()
                }
            )
            await service.publish_message('/custom/topic', custom_msg)
        """
        try:
            encoded_message = Message.encode(message)
            await self.redis_client.publish(channel, encoded_message)
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            raise

    async def publish_messages_raw(self, channel: str, message_raw: Any) -> None:
        """ 发送原始消息到 Redis 的指定 channel """
        try:
            await self.redis_client.publish(channel, message_raw)
        except aioredis.ConnectionError:
            self.logger.error("Redis connection lost while publishing message")
            if await self._reconnect():
                await self.redis_client.publish(channel, message_raw)
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")

    async def get_redis_key(self, key: str) -> Optional[Any]:
        """获取 Redis 中指定 key 的值"""
        if not self.redis_client:
            raise ServiceError("Redis client is not initialized")

        try:
            value = await self.redis_client.get(key)
            if value is None:
                self.logger.warning(f"Key {key} not found in Redis.")
            return value
        except aioredis.ConnectionError:
            self.logger.error("Redis connection lost while getting key")
            if await self._reconnect():
                return await self.redis_client.get(key)
        except Exception as e:
            self.logger.error(f"Error getting key {key} from Redis: {e}")
            raise

    async def set_redis_key(self, key: str, value: Any, ex: Optional[int] = None) -> None:
        """设置 Redis 中指定 key 的值"""
        if not self.redis_client:
            raise ServiceError("Redis client is not initialized")

        try:
            if ex:
                # 设置键值并设置过期时间，单位为秒
                await self.redis_client.setex(key, ex, value)
            else:
                # 如果没有指定过期时间，直接设置
                await self.redis_client.set(key, value)
            self.logger.info(f"Successfully set value for key {key}")
        except aioredis.ConnectionError:
            self.logger.error("Redis connection lost while setting key")
            if await self._reconnect():
                await self.redis_client.set(key, value)
        except Exception as e:
            self.logger.error(f"Error setting key {key} in Redis: {e}")
            raise
