import sys
sys.path.append(".")
del sys


import time
import unittest
import unittest.mock
import asyncio
from typing import (
    List,
    Tuple,
    Callable,
    Awaitable,
    Coroutine,
)

from src.rlim import (
    RateLimiter,
    Rate,
    Limit,
)


class _time:
    def __init__(self) -> None:
        self.stack: List[float] = list()
        self.current: float = time.monotonic()
    
    def reset(self) -> None:
        self.stack = list()
        self.current = time.monotonic()

    def sleep(self, duration: float) -> None:
        self.stack.append(duration)
        self.current += duration
    
    def internal_sleep(self, duration: float) -> None:
        self.current += duration

    async def async_sleep(self, duration: float) -> None:
        self.sleep(duration)

    def verify(
        self, test_case: unittest.TestCase, expected: List[float]
    ) -> None:
        test_case.assertEqual(len(expected), len(self.stack))
        for a, b in zip(expected, self.stack):
            test_case.assertTrue(abs(a - b) <= 0.01)

    def monotonic(self) -> float:
        return self.current


TIME = _time()


class RLTester:
    bfn_sync_ret_tp = Callable[[Callable[[], None]], None]
    bfn_async_ret_tp = Callable[[Callable[[], None]], Awaitable[None]]
    argsets = [
        (False, False, 0),
        (False, False, 1),
        (True, False, 0),
        (True, False, 1)
    ]
    expectations = [
        [
                  0.1,
            0.4,  0.2,
            0.3,  0.3,
            0.2,  0.4,
            0.1,  0.5,
            7.5,  0.6,
        ],
        [
                  0.1,
            1.4,  0.2,
            1.3,  0.3,
            1.2,  0.4,
            1.1,  0.5,
            4.5,  0.6,
        ],
        [
            10.0, 0.1,
            0.4,  0.2,
            0.3,  0.3,
            0.2,  0.4,
            0.1,  0.5,
            7.5,  0.6,
        ],
        [
            11.0, 0.1,
            1.4,  0.2,
            1.3,  0.3,
            1.2,  0.4,
            1.1,  0.5,
            4.5,  0.6,
        ]
    ]

    def sleepfn(self, duration: float) -> Callable[[], None]:
        def sleeper() -> None:
            TIME.sleep(duration)
        return sleeper

    def build_rl(
        self, safestart: bool, throw: bool, variation: float
    ) -> RateLimiter:
        return RateLimiter(
            Rate(2), Limit(5, 10),
            safestart=safestart,
            throw=throw,
            variation=variation
        )

    def sync_test(
        self, test_case: unittest.TestCase,
        buildfn: Callable[
            [RateLimiter],
            "RLTester.bfn_sync_ret_tp"
        ]
    ) -> None:
        for args, expected in zip(self.argsets, self.expectations):
            TIME.reset()
            fn = buildfn(self.build_rl(*args))

            for i in range(1, 7):
                fn(self.sleepfn(i / 10))
            
            TIME.verify(test_case, expected)
    
    async def _async_test(
        self, test_case: unittest.TestCase,
        buildfn: Callable[
            [RateLimiter],
            "RLTester.bfn_async_ret_tp"
        ], args: Tuple[bool, bool, float], expected: List[float]
    ) -> None:
        TIME.reset()
        fn = buildfn(self.build_rl(*args))

        for i in range(1, 7):
            await fn(self.sleepfn(i / 10))
        
        TIME.verify(test_case, expected)

    async def _concurrent_async_test(
        self, test_case: unittest.TestCase,
        buildfn: Callable[
            [RateLimiter],
            "RLTester.bfn_async_ret_tp"
        ], args: Tuple[bool, bool, float], expected: List[float]
    ) -> None:
        TIME.reset()
        fn = buildfn(self.build_rl(*args))

        tasks: List[Coroutine] = list()

        for i in range(1, 7):
            tasks.append(asyncio.create_task(fn(self.sleepfn(i / 10))))
        
        await asyncio.gather(*tasks)

        TIME.verify(test_case, expected)

    async def async_test(
        self, test_case: unittest.TestCase,
        buildfn: Callable[
            [RateLimiter],
            "RLTester.bfn_async_ret_tp"
        ]
    ) -> None:
        for args, expected in zip(self.argsets, self.expectations[:1]):
            await self._async_test(test_case, buildfn, args, expected)
            await self._concurrent_async_test(
                test_case, buildfn, args, expected
            )
