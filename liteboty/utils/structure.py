import asyncio
from typing import Any, Optional


class Queue(object):
    def __init__(self, size):
        self.size = size
        self.queue = []

    def append(self,obj):
        if len(self.queue) < self.size:
            self.queue.append(obj)
        else:
            self.queue.pop(0)
    
    def pop(self):
        if self.queue:
            return self.queue.pop(0)
        else:
            return None


class AsyncQueue:
    """异步队列实现"""

    def __init__(self, maxsize: int = 0):
        self.maxsize = maxsize
        self._queue = asyncio.Queue(maxsize=maxsize)

    async def put(self, item: Any) -> None:
        """添加元素到队列"""
        if 0 < self.maxsize <= self._queue.qsize():
            try:
                self._queue.get_nowait()  # 移除最旧的元素
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(item)

    async def get(self) -> Optional[Any]:
        """从队列获取元素"""
        try:
            return await self._queue.get()
        except asyncio.QueueEmpty:
            return None

    def qsize(self) -> int:
        """返回队列当前大小"""
        return self._queue.qsize()
