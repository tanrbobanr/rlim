"""The core functionality of `rlim`.

:copyright: (c) 2023 Tanner B. Corcoran
:license: Apache 2.0, see LICENSE for more details.

"""

__author__ = "Tanner B. Corcoran"
__license__ = "Apache 2.0 License"
__copyright__ = "Copyright (c) 2023 Tanner B. Corcoran"


import sys
import collections
import functools
import threading
import asyncio
import time
from typing import (
    Union,
    Optional,
    TypeVar,
    Type,
    overload,
    Callable,
    Awaitable,
)
from types import TracebackType

from . import (
    errors,
    utils,
)

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


_P = ParamSpec("_P")
_R_co = TypeVar("_R_co", covariant=True)


class Rate:
    __slots__ = ("rate",)
    def __init__(
        self, calls: Union[int, float], period_seconds: Union[int, float] = 1
    ) -> None:
        """Represents a constant rate (`calls` number of calls every
        `period_seconds` seconds). a `Rate` instance `Rate(C, S)` is
        equivalent to a `Limit` instance `Limit(1, C/S)`.

        Example
        -------
        If a rate of 2 calls per second is used, the rate-limited
        function will be able to be called once every 0.5 seconds.

        """
        # seconds per call
        self.rate = period_seconds / calls

    def _verify(
        self, stack: "collections.deque[float]", current: float
    ) -> Optional[float]:
        """If a pause is required, return the pause duration."""
        if stack:
            return self.rate - (current - stack[-1])


class Limit:
    __slots__ = ("calls", "seconds")
    def __init__(
        self, calls: Union[int, float], seconds: Union[int, float]
    ) -> None:
        """Represents a max call limit (a maximum of `calls` number of
        calls in the last `seconds` number of seconds).

        Example
        -------
        If a limit of 10 calls every 2 seconds is used, the rate-
        limited function will be able to be called at any speed for the
        first 10 calls, then a rate limit will be imposed.

        """
        self.calls = calls
        self.seconds = seconds
    
    def _verify(
        self, stack: "collections.deque[float]", current: float
    ) -> Optional[float]:
        """If a pause is required, return the pause duration."""
        if len(stack) >= self.calls:
            return self.seconds - (current - stack[-self.calls])


def placeholder(func: Callable[_P, _R_co]) -> Callable[_P, _R_co]:
    """Create a wrapper with systems for implementing a rate limiter.
    Works similarly to the `~RateLimiter.apply` method, but with
    `rate_limiter` set to `None`.

    """
    return RateLimiter.apply(None, func)


class RateLimiter:
    """The main class used for rate limiting. An instance of this class
    can be used as function decorators and context managers (including
    async).
    
    """
    @overload
    def __init__(
        self, *criteria: Union[Rate, Limit], safestart: bool = False,
        throw: bool = False, variation: float = 0
    ) -> None: ...
    @overload
    def __init__(
        self, *criteria: Union[Rate, Limit], safestart: bool = False,
        throw: bool = False, variation: float = 0,
        loop: asyncio.AbstractEventLoop
    ) -> None: ...
    def __init__(
        self, *criteria: Union[Rate, Limit], safestart: bool = False,
        throw: bool = False, variation: float = 0,
        loop: asyncio.AbstractEventLoop = None
    ) -> None:
        """
        Arguments
        ---------
        *criteria : Rate or Limit
            The rate limit criteria.
        safestart : bool, default=False
            If True, the stack will be fully preloaded with the current
            time, such that all rate limits will be maxed out. This can
            be useful for ensuring rate limits are not exceeded during
            testing/development.
        throw : bool, default=False
            If True, `RateLimitExceeded` will be raised if the rate
            limit is exceeded.
        variation: float, default=0
            If defined, add this value to the calculated wait time. This
            can be used to account for slight differences in the
            function call time and the time at which anything within the
            function that needs to be rate limited gets called.

        Examples
        --------
        Using a decorator:
        ```
        @RateLimiter(Rate(2), Limit(20, 10))
        def f(...) -> ...:
            ...
        @RateLimiter(Rate(2), Limit(20, 10))
        async def f(...) -> ...:
            ...
        ```
        Context manager:
        ```
        rl = RateLimiter(Rate(2), Limit(20, 10))
        def f(...) -> ...:
            with rl:
                ...
        async def f(...) -> ...:
            async with rl:
                ...
        ```
        Using `.apply`:
        ```
        rl = RateLimiter(Rate(2), Limit(20, 10))
        def f(...) -> ...:
            ...
        f = rl.apply(f)
        async def f(...) -> ...:
            ...
        f = rl.apply(f)
        ```

        """
        if not len(criteria):
            raise ValueError("at least one criteria must be provided")
        self._criteria = criteria
        self._stacklen = self._maxcalls(*criteria)
        self._stack = collections.deque(
            ([time.monotonic()] * self._stacklen if safestart else []),
            maxlen=self._stacklen
        )
        self._safestart = safestart
        self._throw = throw
        self._variation = variation
        self._slock = threading.Lock()

        # asyncio lock can be passed an AbstractEventLoop in <3.9
        if sys.version_info >= (3, 9):
            self._alock = asyncio.Lock()
        else:
            self._alock = asyncio.Lock(loop=loop)

    @staticmethod
    def _maxcalls(*criteria: Union[Rate, Limit]) -> int:
        """Get the maximum number of timestamps required to be stored."""
        calls = [c.calls for c in criteria if isinstance(c, Limit)]
        return max(calls) if calls else 1

    def copy(self, **overrides) -> "RateLimiter":
        """Create a copy of this `RateLimiter` instance with optional
        keyword `overrides` applied during instantiation.

        """
        return RateLimiter(
            *self._criteria,
            **{
                "safestart": self._safestart,
                "throw": self._throw,
                "variation": self._variation,
                **overrides
            }
        )

    @overload
    def apply(self, func: Callable[_P, _R_co]) -> Callable[_P, _R_co]: ...
    @overload
    def apply(
        self, func: Callable[_P, Awaitable[_R_co]]
    ) -> Callable[_P, Awaitable[_R_co]]: ...
    def apply(self, func):
        """Create a new wrapper that wraps the input function such that
        it is rate limited by this rate limiter.

        Returns
        -------
        The new (wrapped) function.
        
        """
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                rl = utils.rl_get(wrapper, True)
                if rl and utils.rl_enabled(wrapper, True):
                    async with rl:
                        return await func(*args, **kwargs)
                else:
                    return await func(*args, **kwargs)
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                rl = utils.rl_get(wrapper, True)
                if rl and utils.rl_enabled(wrapper, True):
                    with rl:
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

        # set states
        utils.rl_setstate(
            wrapper, rate_limiter=self, enabled=True, ignore=True
        )

        return wrapper

    __call__ = apply

    def _verify(self, current: float) -> Optional[float]:
        """Get the required sleep time (if any) given a timestamp
        (monotonic).

        """
        verifs = [
            crit._verify(self._stack, current) for crit in self._criteria
        ]
        verifs_notnone = [v for v in verifs if v is not None]
        if verifs_notnone:
            max_duration = max(verifs_notnone)
            if self._variation:
                diff = max_duration + self._variation
                return diff if diff > 0 else None
            return max([0, max_duration])
    
    def _increment(self, offset: Optional[float]) -> None:
        """Add the current time to the stack with an optional offset."""
        if offset:
            if offset < 0:
                offset = 0
        else:
            offset = 0
        self._stack.append(time.monotonic() + offset)
    
    def _verify_and_increment(self) -> Optional[float]:
        """Call `._verify` with the current time, then call
        `._increment`.
        
        """
        duration = self._verify(time.monotonic())
        self._increment(duration)
        return duration

    def __enter__(self) -> None:
        with self._slock:
            duration = self._verify_and_increment()
        if duration:
            if self._throw:
                raise errors.RateLimitExceeded(duration)
            time.sleep(duration)

    def __exit__(
        self, exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        return

    async def __aenter__(self) -> "RateLimiter":
        async with self._alock:
            with self._slock:
                duration = self._verify_and_increment()
        if duration:
            if self._throw:
                raise errors.RateLimitExceeded(duration)
            await asyncio.sleep(duration)

    async def __aexit__(
        self, exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        return
