"""A modern Python rate limiting package.

:copyright: (c) 2023 Tanner B. Corcoran
:license: Apache 2.0, see LICENSE for more details.

"""

__title__ = "rlim"
__author__ = "Tanner B. Corcoran"
__email__ = "tannerbcorcoran@gmail.com"
__license__ = "Apache 2.0 License"
__copyright__ = "Copyright (c) 2023 Tanner B. Corcoran"
__version__ = "1.0.0"
__description__ = "A modern Python rate limiting package"
__url__ = "https://github.com/tanrbobanr/rlim"
__download_url__ = "https://pypi.org/project/rlim/"


from .ratelimiter import (
    RateLimiter,
    placeholder,
    Rate,
    Limit,
)
from .bundle import Bundle
from .utils import (
    has_rl,
    ensure_rl,
    rl_set,
    rl_strip,
    rl_get,
    rl_enable,
    rl_disable,
    rl_enabled,
    rl_getstate,
    rl_setstate,
)
from .errors import (
    RateLimitExceeded,
    RateLimiterError,
)


__all__ = (
    # ratelimiter
    "Rate",
    "Limit",
    "RateLimiter",
    "placeholder",

    # bundle
    "Bundle",

    # utils
    "has_rl",
    "ensure_rl",
    "rl_set",
    "rl_strip",
    "rl_get",
    "rl_enable",
    "rl_disable",
    "rl_enabled",
    "rl_getstate",
    "rl_setstate",

    # errors
    "RateLimitExceeded",
    "RateLimiterError",
)
