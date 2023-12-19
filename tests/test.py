import sys
import logging
import random
import unittest
import unittest.mock
import string
from typing import (
    List,
    Tuple,
    TypeVar,
    Callable,
    Generator,
    Mapping,
)
if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

sys.path.append(".")
from src.rlim import (
    RateLimiter,
    Rate,
    Limit,
    placeholder,
    Bundle,
    has_rl,
    ensure_rl,
    rl_set,
    rl_strip,
    rl_get,
    rl_enable,
    rl_disable,
    rl_enabled,
    rl_getstate,
    RateLimiterError,
)
from ratelimit_tester import (
    RLTester,
    TIME,
)


# ignore asyncio warnings as the mock of `time.monotonic` will cause
# `asyncio.base_events.BaseEventLoop._run_once` to log a warning
logging.getLogger("asyncio").setLevel(40)


_P = ParamSpec("_P")
_R_co = TypeVar("_R_co", covariant=True)
DecoratorType = Callable[[Callable[_P, _R_co]], Callable[_P, _R_co]]


@unittest.mock.patch("time.monotonic", TIME.monotonic)
@unittest.mock.patch("time.sleep", TIME.sleep)
class Tests(unittest.TestCase):
    @staticmethod
    def _create_ratelimiters(count: int) -> Tuple[RateLimiter, ...]:
        def _rlgen() -> Generator[RateLimiter, None, None]:
            for _ in range(count):
                yield RateLimiter(
                    Rate(random.randint(1, 100)),
                    Limit(random.randint(1, 100), random.randint(1, 100)),
                )
        return tuple(_rlgen())

    @staticmethod
    def _create_bundle(count: int) -> Tuple[Bundle, Tuple[RateLimiter, ...]]:
        if count > 26:
            raise ValueError("'count' must be between 0 and 26 (inclusive)")

        ratelimiters = Tests._create_ratelimiters(count)

        bdl = Bundle(
            **{
                string.ascii_lowercase[i]:rl
                for i, rl in enumerate(ratelimiters)
            }
        )
        return (bdl, ratelimiters)
    
    @staticmethod
    def _create_class(count: int, deco: DecoratorType = None) -> type:
        if count > 26:
            raise ValueError("'count' must be between 0 and 26 (inclusive)")
        def _fngen() -> Generator[Callable[[type], None], None, None]:
            for i in range(count):
                def f(self) -> None: ...
                f.__name__ = f.__module__ = string.ascii_lowercase[i]
                if deco:
                    f = deco(f)
                yield f
        class meta(type):
            def __prepare__(mcs, bases, **kwargs) -> Mapping:
                return {
                    string.ascii_lowercase[i]:f
                    for i, f in enumerate(_fngen())
                }
        class C(metaclass=meta):
            pass
        return C

    @staticmethod
    def _rl_cmp(
        a: RateLimiter, b: RateLimiter
    ) -> Tuple[bool, bool, bool, bool]:
        return (
            a._criteria == b._criteria,
            a._safestart == b._safestart,
            a._throw == b._throw,
            a._variation == b._variation,
        )

    def _rl_cmp_assert(
        self, a: RateLimiter, b: RateLimiter, spec: List[bool] = None
    ) -> None:
        spec = spec or ([True] * 4)
        for x, y in zip(spec, self._rl_cmp(a, b)):
            self.assertEqual(x, y)

    def test_RateLimiter__apply(self) -> None:
        def buildfn(rl: RateLimiter) -> RLTester.bfn_sync_ret_tp:
            def f(sleepfn: Callable[[], None]) -> None:
                sleepfn()
            f = rl.apply(f)
            return f
        RLTester().sync_test(self, buildfn)

    def test_RateLimiter__decorator(self) -> None:
        def buildfn(rl: RateLimiter) -> RLTester.bfn_sync_ret_tp:
            @rl
            def f(sleepfn: Callable[[], None]) -> None:
                sleepfn()
            return f
        RLTester().sync_test(self, buildfn)

    def test_RateLimiter__contextmanager(self) -> None:
        def buildfn(rl: RateLimiter) -> RLTester.bfn_sync_ret_tp:
            def f(sleepfn: Callable[[], None]) -> None:
                with rl:
                    sleepfn()
            return f
        RLTester().sync_test(self, buildfn)

    def test_RateLimiter_copy__nooverride(self) -> None:
        rl = RateLimiter(Rate(2), Limit(10, 2), safestart=True, variation=2.5)
        rl_copy = rl.copy()
        self._rl_cmp_assert(rl, rl_copy, [1, 1, 1, 1])

    def test_RateLimiter_copy__override(self) -> None:
        rl = RateLimiter(Rate(2), Limit(10, 2), safestart=True, variation=2.5)
        rl_copy = rl.copy(throw=True, safestart=False, variation=5.2)
        self.assertEqual(rl._criteria, rl_copy._criteria)
        self.assertEqual(rl_copy._safestart, False)
        self.assertEqual(rl_copy._throw, True)
        self.assertEqual(rl_copy._variation, 5.2)
    
    def test_placeholder(self) -> None:
        C = self._create_class(1, placeholder)
        self.assertEqual(rl_getstate(C.a), (None, True))

    def test_has_rl(self) -> None:
        # with placeholder
        C = self._create_class(1, placeholder)
        self.assertTrue(has_rl(C.a))

        # without placeholder
        C = self._create_class(1)
        self.assertFalse(has_rl(C.a))

    def test_ensure_rl(self) -> None:
        C = self._create_class(1, placeholder)
        ensure_rl(C.a)

    def test_ensure_rl__missing(self) -> None:
        C = self._create_class(1)
        with self.assertRaises(RateLimiterError):
            ensure_rl(C.a)

    def test_rl_set(self) -> None:
        a ,= self._create_ratelimiters(1)
        C = self._create_class(1, placeholder)
        rl_set(C.a, a)
        self.assertEqual(rl_getstate(C.a), (a, True))

    def test_rl_set__missing(self) -> None:
        C = self._create_class(1)
        with self.assertRaises(RateLimiterError):
            rl_set(C.a, None)

    def test_rl_set__missing_ignore(self) -> None:
        C = self._create_class(1)
        rl_set(C.a, None, ignore=True)
        self.assertEqual(rl_get(C.a), None)

    def test_rl_strip(self) -> None:
        C = self._create_class(1, placeholder)
        C.a = rl_strip(C.a)
        self.assertFalse(has_rl(C.a))

    def test_rl_strip__missing(self) -> None:
        C = self._create_class(1)
        with self.assertRaises(RateLimiterError):
            C.a = rl_strip(C.a)

    def test_rl_strip__missing_ignore(self) -> None:
        C = self._create_class(1)
        C.a = rl_strip(C.a, ignore=True)

    def test_rl_get(self) -> None:
        C = self._create_class(1, placeholder)
        self.assertEqual(rl_get(C.a), None)

    def test_rl_get__missing(self) -> None:
        C = self._create_class(1)
        with self.assertRaises(RateLimiterError):
            rl_get(C.a)

    def test_rl_get__missing_ignore(self) -> None:
        C = self._create_class(1)
        self.assertIsNone(rl_get(C.a, ignore=True))

    def test_rl_enable_disable(self) -> None:
        C = self._create_class(1, placeholder)

        # disable
        rl_disable(C.a)
        self.assertFalse(rl_enabled(C.a))

        # enable
        rl_enable(C.a)
        self.assertTrue(rl_enabled(C.a))

    def test_rl_enable_disable__missing(self) -> None:
        C = self._create_class(1)

        # disable
        with self.assertRaises(RateLimiterError):
            rl_disable(C.a)
        
        # enable
        with self.assertRaises(RateLimiterError):
            rl_enable(C.a)

    def test_rl_enable_disable__missing_ignore(self) -> None:
        C = self._create_class(1)

        # disable
        rl_enable(C.a, ignore=True)
        self.assertTrue(rl_enabled(C.a, ignore=True))

        # enable
        rl_disable(C.a, ignore=True)
        self.assertFalse(rl_enabled(C.a, ignore=True))

    def test_rl_getstate(self) -> None:
        # doesn't need any special tests - it's essentially just a
        # combination of `rl_get` and `rl_enabled`
        C = self._create_class(1, placeholder)

    def test_Bundle_init(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertIn("a", bdl._rate_limiters)
        self.assertEqual(bdl._rate_limiters["a"], a)

    def test_Bundle_contains(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertIn("a", bdl)

    def test_Bundle_getitem(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertEqual(bdl["a"], a)
        with self.assertRaises(KeyError):
            bdl["b"]

    def test_Bundle_get(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertEqual(bdl.get("a"), a)
        with self.assertRaises(KeyError):
            bdl.get("b")
        self.assertEqual(bdl.get("b", "MISSING"), "MISSING")

    def test_Bundle_setitem(self) -> None:
        bdl, [a] = self._create_bundle(1)
        bdl["b"] = None
        self.assertIn("b", bdl)
        self.assertEqual(bdl["b"], None)
    
    def test_Bundle_delitem(self) -> None:
        bdl, [a, b] = self._create_bundle(2)
        self.assertIn("b", bdl)
        del bdl["b"]
        self.assertNotIn("b", bdl)
    
    def test_Bundle_wrap(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertFalse(a._throw)
        C = self._create_class(1, placeholder)
        C = bdl._wrap(C, ignore=False, copy=True, throw=True)
        inst = C()
        self.assertNotEqual(rl_get(inst.a), a)
        self._rl_cmp_assert(rl_get(inst.a), a, [1, 1, 0, 1])
        self.assertTrue(rl_get(inst.a)._throw)

    def test_Bundle_decorate(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertFalse(a._throw)
        C = self._create_class(1, placeholder)
        C = bdl.decorate(throw=True)(C)
        inst = C()
        self.assertNotEqual(rl_get(inst.a), a)
        self._rl_cmp_assert(rl_get(inst.a), a, [1, 1, 0, 1])
        self.assertTrue(rl_get(inst.a)._throw)

    def test_Bundle_call(self) -> None:
        bdl, [a] = self._create_bundle(1)
        C = self._create_class(1, placeholder)
        C = bdl(C)
        inst = C()
        self.assertNotEqual(rl_get(inst.a), a)
        self._rl_cmp_assert(rl_get(inst.a), a)
    
    def test_Bundle_bake__apply(self) -> None:
        bdl, [a] = self._create_bundle(1)
        C = self._create_class(1, placeholder)
        bdl.bake(copy=False, throw=True)

        inst_a = C()
        bdl.apply(inst_a)
        self.assertEqual(rl_get(inst_a.a), a)

        inst_b = C()
        bdl.apply(inst_b, copy=True)
        self.assertNotEqual(rl_get(inst_b.a), a)
        self._rl_cmp_assert(rl_get(inst_b.a), a, [1, 1, 0, 1])
        self.assertTrue(rl_get(inst_b.a)._throw)
    
    def test_Bundle_bake__call(self) -> None:
        bdl, [a] = self._create_bundle(1)
        C = self._create_class(1, placeholder)
        bdl.bake(copy=False, throw=True)

        C = bdl(C)
        inst = C()
        self.assertEqual(rl_get(inst.a), a)
        
    def test_Bundle_bake__decorate(self) -> None:
        bdl, [a] = self._create_bundle(1)
        bdl.bake(copy=False, throw=True)

        C1 = self._create_class(1, placeholder)
        C1 = bdl.decorate()(C1)
        inst_a = C1()
        bdl.decorate()(inst_a)
        self.assertEqual(rl_get(inst_a.a), a)


        C2 = self._create_class(1, placeholder)
        C2 = bdl.decorate(copy=True)(C2)
        inst_b = C2()
        self.assertNotEqual(rl_get(inst_b.a), a)
        self._rl_cmp_assert(rl_get(inst_b.a), a, [1, 1, 0, 1])
        self.assertTrue(rl_get(inst_b.a)._throw)

    def test_Bundle_apply__ignore__missing_func(self) -> None:
        bdl, [a, b] = self._create_bundle(2)
        C = self._create_class(1, placeholder)
        inst = C()
        bdl.apply(inst, ignore=True, copy=False)
        self.assertEqual(rl_get(inst.a), a)
    
    def test_Bundle_apply__noignore__missing_func(self) -> None:
        bdl, [a, b] = self._create_bundle(2)
        C = self._create_class(1, placeholder)
        inst = C()
        with self.assertRaises(RateLimiterError):
            bdl.apply(inst)
    
    def test_Bundle_apply__ignore__missing_placeholder(self) -> None:
        bdl, [a, b] = self._create_bundle(2)
        C = self._create_class(2)
        C.a = placeholder(C.a) # `.a` has placeholder now, `.b` doesn't
        self.assertTrue(has_rl(C.a))
        self.assertFalse(has_rl(C.b))
        inst = C()
        bdl.apply(inst, ignore=True, copy=False)
        self.assertFalse(has_rl(inst.b))
        self.assertEqual(rl_get(inst.a), a)
    
    def test_Bundle_apply__noignore__missing_placeholder(self) -> None:
        bdl, [a, b] = self._create_bundle(2)
        C = self._create_class(2)
        C.a = placeholder(C.a) # `.a` has placeholder now, `.b` doesn't
        self.assertTrue(has_rl(C.a))
        self.assertFalse(has_rl(C.b))
        inst = C()
        with self.assertRaises(RateLimiterError):
            bdl.apply(inst)
    
    def test_Bundle_apply__copy(self) -> None:
        bdl, [a] = self._create_bundle(1)
        C = self._create_class(1, placeholder)
        inst = C()
        bdl.apply(inst, copy=True)
        self.assertNotEqual(rl_get(inst.a), a)
        self._rl_cmp_assert(rl_get(inst.a), a)
    
    def test_Bundle_apply__override__copy(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertFalse(a._throw) # better to not assume
        C = self._create_class(1, placeholder)
        inst = C()
        bdl.apply(inst, copy=True, throw=True)
        self.assertNotEqual(rl_get(inst.a), a)
        self._rl_cmp_assert(rl_get(inst.a), a, [1, 1, 0, 1])
        self.assertTrue(rl_get(inst.a)._throw)
    
    def test_Bundle_apply__override__nocopy(self) -> None:
        bdl, [a] = self._create_bundle(1)
        self.assertFalse(a._throw) # better to not assume
        C = self._create_class(1, placeholder)
        inst = C()
        bdl.apply(inst, copy=False, throw=True)
        self.assertEqual(rl_get(inst.a), a)
        self.assertFalse(a._throw)


@unittest.mock.patch("time.monotonic", TIME.monotonic)
@unittest.mock.patch("asyncio.sleep", TIME.async_sleep)
class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_RateLimiter__apply(self) -> None:
        def buildfn(rl: RateLimiter) -> RLTester.bfn_async_ret_tp:
            async def f(sleepfn: Callable[[], None]) -> None:
                sleepfn()
            f = rl.apply(f)
            return f
        await RLTester().async_test(self, buildfn)

    async def test_RateLimiter__decorator(self) -> None:
        def buildfn(rl: RateLimiter) -> RLTester.bfn_async_ret_tp:
            @rl
            async def f(sleepfn: Callable[[], None]) -> None:
                sleepfn()
            return f
        await RLTester().async_test(self, buildfn)

    async def test_RateLimiter__contextmanager(self) -> None:
        def buildfn(rl: RateLimiter) -> RLTester.bfn_async_ret_tp:
            async def f(sleepfn: Callable[[], None]) -> None:
                async with rl:
                    sleepfn()
            return f
        await RLTester().async_test(self, buildfn)


def run_tests() -> None:
    if sys.version_info >= (3, 10):
        unittest.main()
    else:
        # we need to make sure `Tests` runs before `AsyncTests` for
        # versions <= 3.9 due to some weird stuff regard the event loop
        # and asyncio.Lock within RateLimiter.__init__
        suite = unittest.TestSuite()
        suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
        suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(
            AsyncTests
        ))
        unittest.TextTestRunner().run(suite)


if __name__ == "__main__":
    run_tests()
