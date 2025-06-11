import asyncio


class TimerLoop:
    def __init__(self,  name, interval, callback, count=None):
        self.interval = interval
        self.callback = callback
        self.name = name
        self.count = count

    def __str__(self):
        return f"TimerLoop({self.name}, {self.interval})"

    async def run(self):
        run_count = 0
        while self.count is None or run_count < self.count:
            start_time = asyncio.get_event_loop().time()
            await self.callback()
            end_time = asyncio.get_event_loop().time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0, self.interval - elapsed_time))

            if self.count is not None:
                run_count += 1

    def stop(self):
        self.count = -1


def get_service_name_from_path(service_path: str) -> str:
    if service_path.startswith("."):
        service_name = service_path[1:]
        return service_name
    return service_path
