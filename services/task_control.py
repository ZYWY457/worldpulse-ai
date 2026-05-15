from threading import Event


class TaskControl:
    def __init__(self):
        self._cancel_event = Event()

    def reset(self):
        self._cancel_event.clear()

    def cancel(self):
        self._cancel_event.set()

    def is_cancelled(self):
        return self._cancel_event.is_set()
