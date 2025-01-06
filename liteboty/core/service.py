import time
import logging
import threading

import redis

from typing import Any, Dict, Optional

from .exceptions import ServiceError


class Service:
    def __init__(
            self,
            name: str,
            config: Optional[Dict[str, Any]] = None,
            global_config: Optional[Dict[str, Any]] = None,
            redis_client: Optional[redis.Redis] = None,
            need_redis: bool = False
    ):
        self.name = name
        self.config = config or {}
        self.global_config = global_config or {}
        self.redis_client = redis_client
        self.subscriber = None
        self.main_thread = None
        self.logger = logging.getLogger(f"liteboty.default")
        self._subscriptions = {}  # 存储订阅信息
        self._running = True
        self._stopped = threading.Event()  # 添加停止事件标志

        if need_redis:
            self._init_redis()

    def _init_redis(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化 Redis 连接和订阅者"""
        self.redis_client = redis_client or redis.StrictRedis(
            host=self.global_config.get('REDIS', {}).get('host', 'localhost'),
            port=self.global_config.get('REDIS', {}).get('port', 6379)
        )
        self.subscriber = self.redis_client.pubsub()

    def _reconnect(self, max_retries: int = None, initial_backoff: float = 1.0) -> bool:
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
                self.subscriber = self.redis_client.pubsub()
                # 重新订阅所有频道
                for channel, callback in self._subscriptions.items():
                    self.subscriber.subscribe(**{channel: callback})
                self.logger.info("Successfully reconnected to Redis")
                return True
            except redis.ConnectionError as e:
                retries += 1
                if max_retries is not None and retries >= max_retries:
                    self.logger.error(f"Failed to reconnect after {retries} attempts")
                    return False

                self.logger.warning(f"Reconnection failed, retrying in {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)  # 指数退避，最大 30 秒
            except Exception as e:
                self.logger.error(f"Unexpected error during reconnection: {e}")
                return False

    def subscribe(self, channel: str, callback: callable) -> None:
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
        self.subscriber.subscribe(**{channel: callback})

        while self._running:
            try:
                message = self.subscriber.get_message(timeout=0.1)
                if message and message['type'] == 'message':
                    try:
                        callback(message['data'])
                    except Exception as e:
                        self.logger.error(f"Error in callback: {e}")
            except redis.ConnectionError as e:
                self.logger.error(f"Redis connection lost: {e}")
                if not self._reconnect():
                    break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                time.sleep(1)

    def start(self):
        """ 启动应用线程，运行应用逻辑 """
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        self.main_thread = thread

    def run(self):
        """ 应用的主逻辑，需要在子类中实现 """
        raise NotImplementedError("需要在子类中覆盖该类")

    def unsubscribe(self, channel: str) -> None:
        """取消订阅"""
        if channel in self._subscriptions:
            self.subscriber.unsubscribe(channel)
            del self._subscriptions[channel]

    def stop(self) -> None:
        """停止服务"""
        self._running = False
        self._stopped.set()  # 设置停止标志
        if self.subscriber:
            self.subscriber.close()

        self._stopped.set()
        self.cleanup()  # 调用子类清理方法

    def cleanup(self) -> None:
        """子类可以覆盖此方法以实现自定义清理逻辑"""
        pass

    def publish_message(self, topic, message):
        """ 发送消息到 Redis 的指定 topic """
        self.redis_client.publish(topic, message)
