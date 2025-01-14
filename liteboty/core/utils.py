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
            await self.callback()
            end_time = asyncio.get_event_loop().time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0, self.interval - elapsed_time))
