from . import models
from . import exceptions
import collections
import functools
import threading
import asyncio
import typing
import time


def _maxrate(*criteria: typing.Union[models.Rate, models.Limit]) -> models.Rate:
    """Return a new ``Rate`` object with the fastest rate that can satisfy all
    criteria at a constant call speed.
    
    """
    return models.Rate(1, max([c.rate if isinstance(c, models.Rate) else
                               c.seconds / c.calls for c in criteria]))


def _maxcalls(*criteria: typing.Union[models.Rate, models.Limit]) -> int:
    """Get the maximum number of timestamps required to be stored.
    
    """
    maxlen = [c.calls for c in criteria if isinstance(c, models.Limit)]
    return max(maxlen) if maxlen else 1


def _wrapper(func, rate_limiter: "RateLimiter" = None):
    """Create a new wrapper function. Used for ``RateLimiter.__call__`` and
    ``placeholder``.
    
    """
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if wrapper.rate_limiter and wrapper.rate_limiter_enabled:
                async with wrapper.rate_limiter:
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if wrapper.rate_limiter and wrapper.rate_limiter_enabled:
                with wrapper.rate_limiter:
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
    wrapper.rate_limiter = rate_limiter
    wrapper.rate_limiter_enabled = True
    return wrapper


def placeholder(func):
    """Create a wrapper with systems for implementing a rate limiter. Works
    similarly to ``RateLimiter``'s __call__ method, but with ``rate_limiter``
    set to ``None`` by default
    
    """
    return _wrapper(func)


def set_rate_limiter(func, rate_limiter: "RateLimiter") -> None:
    """Set the function's rate limiter to ``rate_limiter``. Essentially:
    ```
    func.__dict__["rate_limiter"] = rate_limiter
    ```
    
    """
    func.__dict__["rate_limiter"] = rate_limiter


def set_rate_limiter_enabled(func, rate_limiter_enabled: bool) -> None:
    """Enable or disable a function's rate limiter. Essentially:
    ```
    func.__dict__["rate_limiter_enabled"] = rate_limiter_enabled
    ```
    
    """
    func.__dict__["rate_limiter_enabled"] = rate_limiter_enabled


def get_rate_limiter(func) -> "RateLimiter":
    """Get a function's rate limiter. Essentially:
    ```
    return func.__dict__["rate_limiter"]
    ```
    
    """
    return func.__dict__["rate_limiter"]


def get_rate_limiter_enabled(func) -> bool:
    """Get a function's rate limiter enabled status. Essentially:
    ```
    return func.__dict__["rate_limiter_enabled"]
    ```
    
    """
    return func.__dict__["rate_limiter_enabled"]


class RateLimiter:
    """The main class used for rate limiting. An instance of this class can be
    used as function decorators and context managers (including async).
    
    """
    def __init__(self, *criteria: typing.Union[models.Rate, models.Limit],
                 autorate: bool = False, safestart: bool = False,
                 raise_on_limit: bool = False,
                 concurrent_async: bool = False,
                 ca_deviation: float = 0) -> None:
        """
        Arguments
        ---------
        *criteria : Rate or Limit
            The rate limit criteria.
        autorate : bool, optional, default=False
            If True, criteria with be replaced with a new ``Rate`` configured
            with the fastest rate that can satisfy all criteria at a constant
            call speed.
        safestart : bool, optional, default=False
            If True, the stack will be preloaded with one (current) timestamp.
            This means that the first rate-limited function call will be rate
            limited.
        raise_on_limit : bool, optional, default=False
            If True, ``RateLimitExceeded`` will be raised if the rate limit is
            exceeded with the time required to sleep as its first argument.
        concurrent_async : bool, optional, default=False
            If True, the asyncio lock will be acquired and released solely
            within the ``__aenter__`` method. Additionally, the completion
            timestamp will be added at the end of the ``__aenter__`` method
            instead of in the ``__aexit__`` method.
        ca_deviation : float, optional, default=0
            If ``concurrent_async`` is True, this value will be added flat-rate
            to the wait time. This can be useful in helping account for slight
            variations in the time it takes between the function being called
            and the API request being sent.


        Raises
        ------
        ValueError
            If no criteria are given.
        """
        if len(criteria) < 1:
            raise ValueError("at least one criteria must be provided")
        if autorate:
            self.criteria = [_maxrate(*criteria)]
        else:
            self.criteria = criteria
        default = [time.monotonic()] if safestart else []
        self._stack = collections.deque(default, maxlen=_maxcalls(*criteria))
        self._slock = threading.Lock()
        self._alock = asyncio.Lock()
        self.raise_on_limit = raise_on_limit
        self._concurrent_async = concurrent_async
        self._ca_deviation = ca_deviation
    
    def __call__(self, func):
        wrapper = _wrapper(func, self)
        return wrapper

    def _verify(self, __current: float) -> typing.Union[float, None]:
        """Get the required sleep time (if any) given a timestamp (monotonic).
        
        """
        verifs = [c._verify(self._stack, __current) for c in self.criteria]
        verifs_notnone = [v for v in verifs if v]
        if verifs_notnone:
            return max(verifs_notnone)
    
    def pause(self) -> None:
        with self._slock:
            overtime = self._verify(time.monotonic())
            if overtime:
                if self.raise_on_limit:
                    raise exceptions.RateLimitExceeded(overtime)
                time.sleep(overtime)
            self._stack.append(time.monotonic())
    
    async def apause(self) -> None:
        async with self._alock:
            overtime = self._verify(time.monotonic())
            if self._concurrent_async:
                if overtime:
                    overtime += self._ca_deviation
                else:
                    overtime = self._ca_deviation
            if overtime:
                if self.raise_on_limit:
                    raise exceptions.RateLimitExceeded(overtime)
                await asyncio.sleep(overtime)
            with self._slock:
                self._stack.append(time.monotonic())

    def __enter__(self) -> "RateLimiter":
        with self._slock:
            overtime = self._verify(time.monotonic())
            if overtime:
                if self.raise_on_limit:
                    raise exceptions.RateLimitExceeded(overtime)
                time.sleep(overtime)
    
    def __exit__(self, __type, __val, __tb) -> None:
        with self._slock:
            self._stack.append(time.monotonic())

    async def __aenter__(self) -> "RateLimiter":
        if self._concurrent_async:
            async with self._alock:
                overtime = self._verify(time.monotonic())
                if overtime:
                    overtime += self._ca_deviation
                else:
                    overtime = self._ca_deviation
                if overtime:
                    if self.raise_on_limit:
                        raise exceptions.RateLimitExceeded(overtime)
                    await asyncio.sleep(overtime)
                with self._slock:
                    self._stack.append(time.monotonic())
                return

        await self._alock.acquire()
        overtime = self._verify(time.monotonic())
        if overtime:
            if self.raise_on_limit:
                raise exceptions.RateLimitExceeded(overtime)
            await asyncio.sleep(overtime)
    
    async def __aexit__(self, __type, __val, __tb) -> None:
        if self._concurrent_async:
            return
        with self._slock:
            self._stack.append(time.monotonic())
            self._alock.release()
