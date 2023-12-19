"""RateLimiter bundles used for easy application of multiple RateLimiter
instances to an entire class instance.

:copyright: (c) 2023 Tanner B. Corcoran
:license: Apache 2.0, see LICENSE for more details.

"""

__author__ = "Tanner B. Corcoran"
__license__ = "Apache 2.0 License"
__copyright__ = "Copyright (c) 2023 Tanner B. Corcoran"


import sys
import functools
from typing import (
    TypeVar,
    Type,
    overload,
    Union,
    Dict,
    Callable,
    Any,
    Tuple,
)
from collections.abc import Hashable

from . import (
    ratelimiter,
    errors,
    utils,
)

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec


T = TypeVar("T")
_P = ParamSpec("_P")
MISSING = object()


class Bundle:
    """An object that allows the user to create a bundle of numerous
    rate limiters, with methods for applying them to the methods of a
    given class or class instance.

    See Also
    --------
    `~.apply`
        Apply the rate limiters contained within this bundle to the
        given class instance.
    `~.decorate` and `~.__call__`
        Decorate a class with this bundle such that the contained rate
        limiters are applied to each instance upon creation.
    `~.bake`
        Bake default arguments into this bundle to pass into `~.apply`
        whenever called. This is especially useful if you have multiple
        bundles, each with their own options, that can be applied
        depending on some user input.

    """
    def __init__(self, **rate_limiters: ratelimiter.RateLimiter) -> None:
        self._rate_limiters: Dict[
            Hashable, ratelimiter.RateLimiter
        ] = rate_limiters
        self._baked_overrides: Dict[str, Any] = dict()
    
    def bake(
        self, ignore: bool = MISSING, copy: bool = MISSING,
        **overrides
    ) -> Self:
        """Bake arguments passed into `.apply` from `._wrap`. Baked
        arguments are the lowest priority, and will be overwritten by
        values passed to `.apply` either directly or through
        `.decorate`.

        """
        self._baked_overrides = {
            **{
                k:v for k, v in [("ignore", ignore), ("copy", copy)]
                if v is not MISSING
            },
            **overrides,
        }
        return self

    def __getitem__(self, key: Hashable) -> ratelimiter.RateLimiter:
        return self._rate_limiters[key]
    
    def __contains__(self, key: Hashable) -> bool:
        return self._rate_limiters.__contains__(key)

    @overload
    def get(self, key: Hashable) -> ratelimiter.RateLimiter: ...
    @overload
    def get(
        self, key: Hashable, default: T
    ) -> Union[ratelimiter.RateLimiter, T]: ...
    def get(self, key: Hashable, default: T = MISSING):
        """Get a rate limiter from this `Bundle` given the `key` and an
        optional `default`.
        
        """
        if default is not MISSING and key not in self._rate_limiters:
            return default
        return self[key]
    
    def __setitem__(
        self, key: Hashable, value: ratelimiter.RateLimiter
    ) -> None:
        self._rate_limiters[key] = value

    def __delitem__(self, key: Hashable) -> None:
        del self._rate_limiters[key]

    def apply(
        self, inst: object, ignore: bool = MISSING, copy: bool = MISSING,
        **overrides
    ) -> None:
        """Iteratively apply the rate limiters within this bundle to
        their corresponding functions on the given instance.

        Arguments
        ---------
        `inst` : object
            A class instance that has functions corresponding to the
            names given when instantiating this bundle.
        `ignore` : bool, default=False
            If `True`, no errors will be raised for missing functions or
            functions that are not set up to accept rate limiters.
        `copy` : bool, default=True
            If `True`, the `RateLimiter` instances contained within this
            `Bundle` instance are copied before being applied to the
            functions. Otherwise, the same instances are used.
        `**overrides` : keywords
            Keyword overrides applied during instantiation of the new
            `RateLimiter` instances (only if `copy` is `True`).

        Raises
        ------
        `errors.RateLimiterError`
            If a function corresponding to the function name given
            during `Bundle` instantiation is not found, and `ignore` is
            `False`.
        `errors.RateLimiterError`
            If the function corresponding to the function name given
            during `Bundle` instantiation is not set up to accept rate
            limiters, and `ignore` is `False`.

        """
        ignore, copy, overrides = self._parse_opts(ignore, copy, overrides)
        for fname, rl in self._rate_limiters.items():
            fn = getattr(inst, fname, None)
            # ensure function exists
            if not fn:
                if ignore:
                    continue
                raise errors.RateLimiterError(f"Missing function: {fname!r}")
            
            # ensure function accepts rate limiters
            if not utils.has_rl(fn):
                if ignore:
                    continue
                raise errors.RateLimiterError(
                    f"{fname!r} is not set up for rate limiting"
                    " - use `placeholder`."
                )
            
            # apply
            if copy:
                setattr(inst, fname, rl.copy(**overrides).apply(fn))
            else:
                setattr(inst, fname, rl.apply(fn))

    def _wrap(
        self, cls: Type[T], ignore: bool = MISSING, copy: bool = MISSING,
        **overrides
    ) -> Callable[_P, T]:
        """Create the wrapper for `cls` that wraps its `__init__`
        method. The wrapper creates an instance of `cls` with the
        user-supplied arguments, calls `.apply` on that instance, then
        returns it.

        """
        @functools.wraps(cls)
        def wrapper(*args, **kwargs) -> T:
            inst = cls(*args, **kwargs)
            self.apply(inst, ignore=ignore, copy=copy, **overrides)
            return inst
        return wrapper

    def _parse_opts(
        self, ignore: bool, copy: bool, overrides: Dict[str, Any]
    ) -> Tuple[bool, bool, Dict[str, Any]]:
        """Resolve keyword arguments from `._baked_overrides` and the
        arguments passed here.

        """
        opts = {
            "ignore": False,
            "copy": True,
            **self._baked_overrides,
            **{
                k:v for k, v in [("ignore", ignore), ("copy", copy)]
                if v is not MISSING
            },
            **overrides,
        }
        return (
            opts.pop("ignore"),
            opts.pop("copy"),
            opts,
        )

    def decorate(
        self, ignore: bool = MISSING, copy: bool = MISSING, **overrides
    ) -> Callable[[Type[T]], Callable[_P, T]]:
        """Creates a decorator that wraps `.apply`. Similar to simply
        decorating a class with this `Bundle` instance, except in this
        case, all options available to `.apply` can be changed. The
        two examples below are equivalent:
        ```
        @Bundle(...)
        class C:
            ...
        
        @Bundle(...).decorate()
        class C:
            ...
        ```
        while the following examples are not:
        ```
        @Bundle(...)
        class C:
            ...
        
        @Bundle(...).decorate(copy=False)
        class C:
            ...
        ```

        """
        def decorator(cls: Type[T]) -> Callable[_P, T]:
            return self._wrap(cls, ignore=ignore, copy=copy, **overrides)
        return decorator

    def __call__(self, cls: Type[T]) -> Callable[_P, T]:
        """Wrap the given class using `._wrap`."""
        return self._wrap(cls)
