"""A modern synchronous and asynchronous function rate limiter.

:copyright: (c) 2022 Tanner B. Corcoran
:license: MIT, see LICENSE for more details.

"""

__title__ = "rlim"
__author__ = "Tanner B. Corcoran"
__email__ = "tannerbcorcoran@gmail.com"
__license__ = "MIT License"
__copyright__ = "Copyright (c) 2022 Tanner B. Corcoran"
__version__ = "0.0.1"
__description__ = "A modern synchronous and asynchronous function rate limiter"
__url__ = "https://github.com/tanrbobanr/rlim"
__download_url__ = "https://pypi.org/project/rlim/"

from ._ratelimit import RateLimiter
from ._ratelimit import placeholder
from ._ratelimit import set_rate_limiter
from ._ratelimit import set_rate_limiter_enabled
from ._ratelimit import get_rate_limiter
from ._ratelimit import get_rate_limiter_enabled
from .exceptions import RateLimitExceeded
from .models import Rate
from .models import Limit

__all__ = ("RateLimiter", "placeholder", "set_rate_limiter",
           "set_rate_limiter_enabled", "get_rate_limiter",
           "get_rate_limiter_enabled", "RateLimitExceeded", "Rate", "Limit")
