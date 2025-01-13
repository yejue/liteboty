import asyncio
import heapq

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


class PriorityQueue:
    """使用堆实现的优先级队列"""

    def __init__(self, max_size=None):
        self._queue = []  # 用于存储队列的堆
        self._index = 0   # 用于确保相同优先级时保持插入顺序
        self.max_size = max_size  # 设置最大队列大小，默认不限制

    def push(self, item, priority):
        # 如果队列已达到最大大小，移除优先级最低的元素
        if self.max_size is not None and len(self._queue) >= self.max_size:
            # 弹出优先级最低的元素（堆中最小的元素）
            self.pop()

        # 插入队列，优先级使用负数来保证堆是降序排序
        heapq.heappush(self._queue, (-priority, self._index, item))
        self._index += 1

    def pop(self):
        if self.qsize() == 0:
            return None
        # 弹出队列中的最高优先级项
        _, _, item = heapq.heappop(self._queue)
        return item

    def peek(self):
        # 返回最高优先级项，但不移除
        if self._queue:
            _, _, item = self._queue[0]
            return item
        return None

    def remove(self, condition):
        # 按照条件移除元素，返回被移除的项
        items_to_remove = []
        for i, (_, _, item) in enumerate(self._queue):
            if condition(item):  # 如果条件成立，加入待删除列表
                items_to_remove.append(item)

        # 清除队列中的被删除项
        self._queue = [entry for entry in self._queue if not condition(entry[2])]
        heapq.heapify(self._queue)

        return items_to_remove

    def qsize(self) -> int:
        return len(self._queue)

    def __len__(self):
        # 返回队列的大小
        return len(self._queue)

    def __str__(self):
        # 打印队列的当前状态（按优先级降序排序）
        return ', '.join(f'{item} (Priority: {-priority})' for priority, _, item in self._queue)


if __name__ == '__main__':
    # 示例代码使用
    pq = PriorityQueue(max_size=10)

    # 添加项到队列
    pq.push('task1', 5)
    pq.push('task2', 3)
    pq.push('task3', 8)

    print("当前队列: ", pq)
