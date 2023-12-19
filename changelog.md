# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.0.0] - 2023-11-27

### Added

- The `Bundle` class added, used to bundle various `RateLimiter` instances together to ease the process of applying multiple rate limiter instances to a class instance.
- `variation` parameter added to `RateLimiter`.
- `loop` parameter added to `RateLimiter` to pass the event loop into the asyncio `Lock` on version pre-3.10.
- `has_rl` utility function added to determine if the given function is set up for rate limiting.
- `ensure_rl` utility function added to raise an error if the given function is not set up for rate limiting.
- `rl_strip` utility function added used to remove the rate limiting capability of a function.
- `rl_getstate` utility function added to get both the `RateLimiter` instance and whether or not it is enabled from the given function.
- `rl_setstate` utility function added to set the `RateLimiter` and/or whether or not it is enabled on the given function.

### Changed

- Changed license to Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
- `set_rate_limiter` changed to `rl_set`, `ignore` parameter added.
- `set_rate_limiter_enabled` changed to `rl_enable` and `rl_disable`, `ignore` parameter added.
- `get_rate_limiter` changed to `rl_get`, `ignore` parameter added.
- `get_rate_limiter_enabled` changed to `rl_enabled`, `ignore` parameter added.
- Formally public control variables `rate_limiter` and `rate_limiter_enabled` are now private control variables `_rate_limiter` and `_rate_limiter_enabled`.

### Removed

- `concurrent_async` and `ca_deviation` parameters from `RateLimiter`.

### Updated

- The `RateLimiter`, `Rate`, `Limit`, and `placeholder` classes/functions to have stronger typing, better docstrings, and more robust handling of rate limiting.
