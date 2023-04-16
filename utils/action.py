class ActionSchema:
    def __init__(self, name, handle, queue: bool = True, validate=None):
        self.name = name
        self.handle = handle
        self.queue = queue
        self.validate = validate
