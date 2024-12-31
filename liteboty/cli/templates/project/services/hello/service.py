from liteboty.core import Service


class HelloService(Service):
    def __init__(self, config):
        super().__init__("HaloService", config)

    def run(self) -> None:
        print("Hello")
