

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
