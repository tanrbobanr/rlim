"""Functions used to manipulate rate limiters.

:copyright: (c) 2023 Tanner B. Corcoran
:license: Apache 2.0, see LICENSE for more details.

"""

__author__ = "Tanner B. Corcoran"
__license__ = "Apache 2.0 License"
__copyright__ = "Copyright (c) 2023 Tanner B. Corcoran"


import sys
from typing import (
    TYPE_CHECKING,
    Optional,
    TypeVar,
    Tuple,
    Callable,
)

from . import errors

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from .ratelimiter import RateLimiter
else:
    RateLimiter = None


_P = ParamSpec("_P")
_R_co = TypeVar("_R_co", covariant=True)
MISSING = object()


def has_rl(func: Callable[_P, _R_co]) -> bool:
    """Checks if `func` is set up for rate limiting."""
    return hasattr(func, "_rate_limiter")


def ensure_rl(func: Callable[_P, _R_co]) -> None:
    """Raise a `RateLimiterError` if `func` is not set up for rate
    limiting.
    
    """
    if not has_rl(func):
        raise errors.RateLimiterError(
            f"{func!r} is not set up for rate limiting."
            " Consider using `utils.placeholder` or `~RateLimiter`."
        )


def rl_set(
    func: Callable[_P, _R_co], rate_limiter: "RateLimiter",
    ignore: bool = False
) -> None:
    """Set the rate limiter of `func` to `rate_limiter`. If `func` is
    not set up to accept rate limiting, a `RateLimiterError` will be
    raised (unless `ignore` is `True`).

    """
    if not ignore:
        ensure_rl(func)
    setattr(func, "_rate_limiter", rate_limiter)


def rl_strip(
    func: Callable[_P, _R_co], ignore: bool = False
) -> Callable[_P, _R_co]:
    """Remove rate limiting functionality from the given function. If
    `func` is not set up to accept rate limiting, a `RateLimiterError`
    will be raised (unless `ignore` is `True`).

    """
    if not ignore:
        ensure_rl(func)
        return func.__wrapped__
    try:
        return func.__wrapped__
    except AttributeError:
        return func


def rl_get(
    func: Callable[_P, _R_co], ignore: bool = False
) -> Optional["RateLimiter"]:
    """Get the rate limiter from `func`. If `func` is not set up to
    accept rate limiting, a `RateLimiterError` will be raised (unless
    `ignore` is `True`).

    """
    if not ignore:
        ensure_rl(func)
    return getattr(func, "_rate_limiter", None)


def rl_enable(func: Callable[_P, _R_co], ignore: bool = False) -> None:
    """Enable the rate limiter attached to `func`. If `func` is not set
    up to accept rate limiting, a `RateLimiterError` will be raised
    (unless `ignore` is `True`).
    
    """
    if not ignore:
        ensure_rl(func)
    setattr(func, "_rate_limiter_enabled", True)


def rl_disable(func: Callable[_P, _R_co], ignore: bool = False) -> None:
    """Disable the rate limiter attached to `func`. If `func` is not set
    up to accept rate limiting, a `RateLimiterError` will be raised
    (unless `ignore` is `True`).
    
    """
    if not ignore:
        ensure_rl(func)
    setattr(func, "_rate_limiter_enabled", False)


def rl_enabled(func: Callable[_P, _R_co], ignore: bool = False) -> bool:
    """Check if the rate limiter attached to `func` is enabled. If
    `func` is not set up to accept rate limiting, a `RateLimiterError`
    will be raised (unless `ignore` is `True`).
    
    """
    if not ignore:
        ensure_rl(func)
    return getattr(func, "_rate_limiter_enabled", False)


def rl_getstate(
    func: Callable[_P, _R_co], ignore: bool = False
) -> Tuple[Optional[RateLimiter], bool]:
    """Get the `RateLimiter` instance (if present) and whether or not
    the rate limiter is enabled. If `func` is not set up to accept rate
    limiting, a `RateLimiterError` will be raised (unless `ignore` is
    `True`).
    
    """
    if not ignore:
        ensure_rl(func)
    return (rl_get(func, ignore=True), rl_enabled(func, ignore=True))


def rl_setstate(
    func: Callable[_P, _R_co], rate_limiter: Optional[RateLimiter] = MISSING,
    enabled: bool = MISSING, ignore: bool = False
) -> None:
    """Set the `RateLimiter` instance and/or enable/disable the rate
    limiter attached to `func`. If `func` is not set up to accept rate
    limiting, a `RateLimiterError` will be raised (unless `ignore` is
    `True`).

    """
    if not ignore:
        ensure_rl(func)
    if rate_limiter is not MISSING:
        rl_set(func, rate_limiter, ignore=True)
    if enabled is not MISSING:
        setattr(func, "_rate_limiter_enabled", enabled)
