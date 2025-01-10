
import asyncio
class TimerLoop:
    def __init__(self,  name, interval, callback):
        self.interval = interval
        self.callback = callback
        self.name = name

    def __str__(self):
        return f"TimerLoop({self.name}, {self.interval})"

    async def run(self):
        while True:
            start_time = asyncio.get_event_loop().time()
            # try:
            await self.callback()
            # except Exception as e:
            #     logger.error(f"[ERROR] 定时器 {timer_name} 发生异常：{e}")
            end_time = asyncio.get_event_loop().time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0, self.interval - elapsed_time))