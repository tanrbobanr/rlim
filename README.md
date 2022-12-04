# Install
`pip install rlim`

# What purpose does `rlim` serve?
When working with various APIs, I have found that in some cases the rate limits imposed on the user can be somewhat complex. For example, a single endpoint may have a limit of 3 calls per second *and* 5000 calls per hour (in a few rare instances, I have seen 3 limits for a single endpoint). The two other common rate limiting packages out there ([ratelimit](https://pypi.org/project/ratelimit/) and [ratelimiter](https://pypi.org/project/ratelimiter/)) only allow for a single rate limit to be set (e.g. 300 calls per 30 seconds). Although you could simply decorate a function multiple times, it can very quickly become wasteful in terms of memory and performance. Thus I decided to make a modern memory- and performance-efficient rate limiting module that allows for multiple limits to be imposed on a single rate limiter, as well as combining the best parts of the aforementioned packages.

# How to create and use the RateLimiter
The creation of a `RateLimiter` instance is rather simple, and there are numerous ways to implement it into your code.

## Decorators
A function can be decorated either with a `RateLimiter` instance or with the `placeholder` function decorator. When a function is decorated with either of these, it gains two attributes: `rate_limiter` and `rate_limiter_enabled`. If `rate_limiter` is not `None` and `rate_limiter_enabled` is `True`, the function will be rate limited; otherwise, the function will still run but without any rate limiting. **NOTE**: for all the below examples, the process is identical for async functions / methods.

### Decorating with a `RateLimiter` instance
Below is an example on how you might decorate a function with a new instance, as well as with an existing instance.
```py
from rlim import RateLimiter, Rate, Limit

@RateLimiter(Rate(3), Limit(1000, 3600))
def example():
    ...

rl = RateLimiter(Rate(3), Limit(1000, 3600))

@rl
def example():
    ...
```

### Decorating with `placeholder`
The purpose of `placeholder` is so that you can prepare a function to be rate limited (e.g. in a new class instance) and apply the `RateLimiter` instance afterward (e.g. in \_\_init\_\_). Setting the rate limiter can be done with the `set_rate_limiter` helper method, or by simply setting the function's `rate_limiter` attribute to a `RateLimiter` instance.
```py
from rlim import RateLimiter, Rate, Limit, placeholder, set_rate_limiter

class Example:
    def __init__(self, rl: RateLimiter):
        set_rate_limiter(self.example_method, rl)
    
    @placeholder
    def example_method(self):
        ...

@placeholder
async def example():
    ...

rl = RateLimiter(Rate(3), Limit(1000, 3600))
eg = Example(rl)
example.rate_limiter = rl
```

## Using context managers
Another way to implement this into your code is to simply use a context manager.
```py
from rlim import RateLimiter, Rate, Limit

rl = RateLimiter(Rate(3), Limit(1000, 3600))

def example():
    with rl:
        ...

async def example():
    async with rl:
        ...
```

## Using `pause` and `apause`
In general, the decorator or context manager methods should be used, but if needed, there are also the `pause` and `apause` methods which can be used to simply pause within your code. This comes with the possiblity to exceed the rate limits of the API you are interacting with, as the next timestamp gets added directly after the pause, not after the encapsulated code has completed. So use this with caution.
```py
from rlim import RateLimiter, Rate, Limit

rl = RateLimiter(Rate(3), Limit(1000, 3600))

def example():
    rl.pause()
    ...

async def example():
    await rl.apause()
    ...
```

# List of functions and classes
- RateLimiter [*._ratelimit.RateLimiter*]
    - The main class used to rate limit function calls.
- placeholder [*._ratelimit.placeholder*]
    - Used to prepare a function for rate limiting when a rate limiter instance is not yet available.
- set_rate_limiter [*._ratelimit.set_rate_limiter*]
    - Sets a function's rate limiter.
- set_rate_limiter_enabled [*._ratelimit.set_rate_limiter_enabled*]
    - Enables or disables a function's rate limiter.
- get_rate_limiter [*._ratelimit.get_rate_limiter*]
    - Get a function's rate limiter.
- get_rate_limiter_enabled [*._ratelimit.get_rate_limiter_enabled*]
    - Get a function's rate limiter enabled status
- RateLimitExceeded [*.exceptions.RateLimitExceeded*]
    - An exception raised if `raise_on_limit` is enabled in the `RateLimiter` instance.
- Rate [*.models.Rate*]
    - A criteria for constant-rate limiting.
- Limit [*.models.Limit*]
    - A criteria for quota limiting.
- *._ratelimit._maxrate*
    - An internal method used for creating a new `Rate` instance if `autorate` is set to `True` upon instantiation of the `RateLimiter` instance.
- *._ratelimit._maxcalls*
    - An internal method used for determining the size of the `RateLimiter` instance's `deque`.
- *._ratelimit._wrapper*
    - An internal method used to create the base function wrapper.
