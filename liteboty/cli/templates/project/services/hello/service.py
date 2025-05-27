from liteboty.core import Service


class HelloService(Service):
    def __init__(self, **kwargs):
        super().__init__("HelloService", **kwargs)
        self.add_timer("timer1", interval=0, callback=self.say_somthing, count=1)

    def say_somthing(self):
        self.config.get("welcome_text", "hello...")
