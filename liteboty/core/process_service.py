import asyncio
import importlib
import logging
import time
from multiprocessing import Process, Event
from typing import Any, Dict, Optional


async def _service_main(service_entry_obj, config: Dict[str, Any], global_config: Dict[str, Any], stop_evt: Event):
    """
    Run service in child process event loop
    """
    # Instantiate service via service_entry to stay compatible with custom signatures
    service = service_entry_obj(config=config, global_config=global_config)

    await service.start()

    try:
        # Poll stop event
        while not stop_evt.is_set():
            await asyncio.sleep(0.5)
    finally:
        try:
            await service.stop()
        except Exception as e:
            logging.getLogger("liteboty_default").warning(f"service.stop error: {e}")


def _service_worker(service_path: str, config: Dict[str, Any], global_config: Dict[str, Any], stop_evt: Event):
    """
    Process target: create loop and run service until stop event is set
    """
    # Basic logging for child process
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("liteboty_default")
    logger.info(f"Starting child process for service: {service_path}")

    async def runner():
        try:
            if service_path.startswith('.'):
                # Import relative package from CWD
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path.cwd()))
                try:
                    module = importlib.import_module(service_path.lstrip('.'))
                finally:
                    sys.path.pop(0)
            else:
                module = importlib.import_module(service_path)

            if not hasattr(module, "service_entry"):
                raise ImportError(f"Service 包 {service_path} 必须在 __init__.py 暴露 service_entry")

            service_entry_obj = getattr(module, "service_entry")
            await _service_main(service_entry_obj, config, global_config, stop_evt)

        except Exception as e:
            logger.error(f"Child process for {service_path} crashed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    asyncio.run(runner())


class ProcessServiceProxy:
    """
    Proxy object to manage a service in a separate process while keeping Service-like API.
    """
    def __init__(self, service_path: str, service_name: str, config: Optional[Dict[str, Any]] = None, global_config: Optional[Dict[str, Any]] = None):
        self.name = service_name
        self.service_path = service_path
        self.config = config or {}
        self.global_config = global_config or {}

        self._process: Optional[Process] = None
        self._stop_evt: Optional[Event] = None
        self._running: bool = False
        self._start_time: float = time.time()
        self.logger = logging.getLogger("liteboty_default")

    async def start(self) -> None:
        if self._running and self._process and self._process.is_alive():
            return
        self._stop_evt = Event()
        self._process = Process(
            target=_service_worker,
            args=(self.service_path, self.config, self.global_config, self._stop_evt),
            daemon=True,
        )
        self._process.start()
        self._running = True
        self._start_time = time.time()
        self.logger.info(f"Started process for service: {self.name} (pid={self._process.pid})")

    async def stop(self) -> None:
        if not self._process:
            self._running = False
            return

        self._running = False
        if self._stop_evt:
            self._stop_evt.set()

        # Join with timeout in thread to avoid blocking event loop
        try:
            await asyncio.to_thread(self._process.join, 5.0)
        except Exception:
            pass

        if self._process.is_alive():
            self.logger.warning(f"Terminating service process: {self.name}")
            self._process.terminate()
            try:
                await asyncio.to_thread(self._process.join, 2.0)
            except Exception:
                pass

        self.logger.info(f"Stopped process for service: {self.name}")
        self._process = None
        self._stop_evt = None

    async def restart(self, config: dict, global_config: dict) -> None:
        await self.stop()
        self.config = config
        self.global_config = global_config
        self._running = True
        await self.start()
