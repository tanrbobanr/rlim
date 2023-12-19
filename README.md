# Install
`$ pip install rlim`

# Basic Usage
Create and use a `RateLimiter` instance:
```py
@RateLimiter(Rate(2), Limit(50, 40))
def f():
    ...

@RateLimiter(Rate(2), Limit(50, 40))
async def f():
    ...
```
Apply a `RateLimiter` instance to a function decorated with `placeholder`:
```py
@placeholder
def f():
    ...
rl_set(f, RateLimiter(Rate(2), Limit(50, 40)))

@placeholder
async def f():
    ...
rl_set(f, RateLimiter(Rate(2), Limit(50, 40)))
```
Use an instance as a context manager:
```py
rl = RateLimiter(Rate(2), Limit(50, 40))
def f():
    with rl:
        ...

async def f():
    async with rl:
        ...
```
Notice that in the above, `Rate` and `Limit` are two distinct types. `Rate` is used to define a constant calling speed - for example, `Rate(2)` would equate to `1` call every `0.5` seconds. `Limit` is used to define a maximum number of calls (at *any* speed) within a certain period of time (sliding window) - for example, `Limit(50, 40)` would mean the user could make calls at any speed, so long as they don't surpass 50 calls within the last 40 seconds. Together, this means the user can many calls at a max speed of `0.5s/call`, and must stay below (or equal to) `50` calls in the past `40` seconds.

# Bundles
Bundles allow you to bundle together numerous rate limiters, with methods for applying them to the methods of a given class or class instance. When a bundle is applied to a class instance, the `RateLimiter` instances (or copies of them, if desired) within the bundle will be applied to each of the class's methods upon class instantiation.

Creating a `Bundle`:
```py
bdl = Bundle(
    fn1=RateLimiter(...),
    fn2=RateLimiter(...),
    ...
)
```
Applying a `Bundle` instance to a class:
```py
@bdl
class Example:
    def fn1(self) -> None:
        return
    def fn2(self) -> None:
        return
```
Now, when you create an instance of `Example`, `fn1` and `fn2` will have their corresponding `RateLimiter` instances applied to them.

# Additional Functions/Methods
```py
RateLimiter.copy(**overrides) -> RateLimiter
```
> Create a copy of the `RateLimiter` instance with optional overrides (that will be passed into `RateLimiter.__init__`).

```py
RateLimiter.apply(func: Callable[_P, _R_co]) -> Callable[_P, _R_co]
RateLimiter.apply(func: Callable[_P, Awaitable[_R_co]]) -> Callable[_P, Awaitable[_R_co]]
```
> Manually wrap the given function to use the `RateLimiter` instance for rate limiting. `RateLimiter.__call__` (the function that makes it possible to decorate another function with a `RateLimiter` instance) is simply an alias of `RateLimiter.apply`.

```py
Bundle.apply(
    inst: object,
    ignore: bool = MISSING,
    copy: bool = MISSING,
    **overrides
) -> None
```
> Apply the `RateLimiter` instances in this `Bundle` to the given class instance.
> - `ignore` (default `False`) will make it so `RateLimiterError` will not be raised if a function in the decorated class does not have a corresponding `RateLimiter`.
> - `copy` (default `True`) will make it so copies of the `RateLimiter` instances are applied, instead of the same instances.
> - `**overrides` are keyword overrides that will be passed into `RateLimiter.copy` (only if `copy` is `True`).

```py
Bundle.decorate(
    ignore: bool = MISSING,
    copy: bool = MISSING,
    **overrides
) -> Callable[[Type[T]], Callable[_P, T]]
```
> This function allows the user to have more control over how the `RateLimiter` instances are applied to the decorated class's methods. It returns a decorator. `ignore`, `copy`, and `**overrides` will be passed into `Bundle.apply`.

```py
Bundle.bake(
    ignore: bool = MISSING,
    copy: bool = MISSING,
    **overrides
) -> None
```
> Bake arguments for calls to `Bundle.apply` and `Bundle.decorate` into the `Bundle` instance. Any arguments provided to `Bundle.apply` or `Bundle.decorate` have precedence over baked arguments.
