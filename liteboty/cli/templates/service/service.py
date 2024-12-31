from liteboty.core import Service


class ExampleService(Service):
    def __init__(self, config=None):
        super().__init__("ExampleService", config)

    def message_handler(self, message):
        ...

    def run(self):
        self.logger.info("Starting example service")
        # 订阅消息
        self.subscribe("example_channel", self.message_handler)
