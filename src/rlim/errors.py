"""Generic exceptions used throughout the package.

:copyright: (c) 2023 Tanner B. Corcoran
:license: Apache 2.0, see LICENSE for more details.

"""

__author__ = "Tanner B. Corcoran"
__license__ = "Apache 2.0 License"
__copyright__ = "Copyright (c) 2023 Tanner B. Corcoran"


class RateLimitExceeded(Exception):
    """Rate limit has been exceeded."""


class RateLimiterError(Exception):
    """Generic exception for `rlim` errors."""
