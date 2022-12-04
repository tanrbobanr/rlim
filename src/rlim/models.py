import collections
import typing


class Rate:
    __slots__ = ("rate",)
    def __init__(self, calls: typing.Union[int, float],
                 period_seconds: typing.Union[int, float] = 1) -> None:
        self.rate = period_seconds / calls
    
    def _verify(self, __stack: collections.deque,
                __current: float) -> typing.Union[float, None]:
        if __stack:
            overtime = __current - __stack[-1]
            if overtime < self.rate:
                return self.rate - overtime


class Limit:
    __slots__ = ("calls", "seconds")
    def __init__(self, calls: typing.Union[int, float],
                 seconds: typing.Union[int, float]) -> None:
        self.calls = calls
        self.seconds = seconds
    
    def _verify(self, __stack: collections.deque,
                __current: float) -> typing.Union[float, None]:
        if len(__stack) < self.calls:
            return
        overtime = __current - __stack[-self.calls]
        if overtime < self.seconds:
            return self.seconds - overtime
