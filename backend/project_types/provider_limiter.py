from dataclasses import dataclass
from typing import Dict
from datetime import datetime, timedelta
import random
import asyncio
from loguru import logger
import time
import threading
from project_types.leaky_bucket import LeakyBucket
from project_types.error_types import RateLimitError, TimeoutError
from project_types.request_admission import RequestAdmissionControl


@dataclass
class RateLimitConfig:
    """Configuration for provider-specific rate limits"""

    requests_per_minute: int
    tokens_per_minute: int
    enabled: bool = True
    max_retries: int = 8
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 64.0
    jitter_factor: float = 0.1


class ProviderLimiter:
    """Rate limiter with advanced admission control"""

    _instances: Dict[str, tuple[LeakyBucket, LeakyBucket, RequestAdmissionControl]] = {}
    _backoff_until: Dict[str, datetime] = {}
    _lock = asyncio.Lock()
    _sync_lock = threading.Lock()  # Added for sync operations
    _consecutive_failures: Dict[str, int] = {}

    SAFETY_THRESHOLD = 0.9  # Only use 90% of rate limits

    @classmethod
    def get_limiters(
        cls, provider_type: str, config: RateLimitConfig
    ) -> tuple[LeakyBucket, LeakyBucket, RequestAdmissionControl]:
        """Get or create rate limiters with safety margins"""
        if provider_type not in cls._instances:
            safe_requests_per_minute = int(
                config.requests_per_minute * cls.SAFETY_THRESHOLD
            )
            safe_tokens_per_minute = int(
                config.tokens_per_minute * cls.SAFETY_THRESHOLD
            )

            request_limiter = LeakyBucket(rate_per_minute=safe_requests_per_minute)
            token_limiter = LeakyBucket(rate_per_minute=safe_tokens_per_minute)
            admission_control = RequestAdmissionControl(
                safe_requests_per_minute, safe_tokens_per_minute
            )

            cls._instances[provider_type] = (
                request_limiter,
                token_limiter,
                admission_control,
            )
            cls._backoff_until[provider_type] = datetime.now()
            cls._consecutive_failures[provider_type] = 0

        return cls._instances[provider_type]

    @classmethod
    def _add_jitter(cls, delay: float, config: RateLimitConfig) -> float:
        """Add random jitter to delay"""
        jitter_range = delay * config.jitter_factor
        return delay + random.uniform(-jitter_range, jitter_range)

    @classmethod
    def _get_backoff_delay(cls, provider_type: str, config: RateLimitConfig) -> float:
        """Calculate exponential backoff with jitter"""
        failures = cls._consecutive_failures.get(provider_type, 0)
        base_delay = min(
            config.initial_retry_delay * (2**failures), config.max_retry_delay
        )
        return cls._add_jitter(base_delay, config)

    @classmethod
    def _acquire_sync(
        cls, provider_type: str, config: RateLimitConfig, tokens: int = 0
    ):
        """Synchronous version of rate limit acquisition"""
        if not config.enabled:
            return

        priority = cls._consecutive_failures.get(provider_type, 0)

        for attempt in range(config.max_retries + 1):
            try:
                with cls._sync_lock:
                    now = datetime.now()
                    backoff_until = cls._backoff_until.get(provider_type, now)
                    if now < backoff_until:
                        delay = (backoff_until - now).total_seconds()
                        logger.warning(
                            f"{provider_type}: Global backoff active. Waiting {delay:.2f}s"
                        )
                        time.sleep(delay)

                    request_limiter, token_limiter, admission_control = (
                        cls.get_limiters(provider_type, config)
                    )

                    if not admission_control.can_admit_request_sync(tokens):
                        raise RateLimitError("Request cannot be admitted")

                    admission_control.admit_request_sync(tokens, priority=priority)

                    # Handle request rate limiting
                    timeout = min(30.0, config.max_retry_delay)
                    request_limiter._acquire_sync(1, timeout=timeout, priority=priority)

                    # Handle token rate limiting if needed
                    if tokens > 0:
                        token_limiter._acquire_sync(
                            tokens, timeout=timeout, priority=priority
                        )
                    cls._consecutive_failures[provider_type] = 0
                    return

            except (RateLimitError, TimeoutError) as e:
                if attempt < config.max_retries:
                    delay = cls._get_backoff_delay(provider_type, config)
                    logger.warning(
                        f"{provider_type}: Rate limit error: {str(e)}, "
                        f"attempt {attempt + 1}/{config.max_retries + 1}. "
                        f"Backing off for {delay:.2f}s"
                    )
                    time.sleep(delay)
                    priority += 1
                    continue
                raise
            except Exception as e:
                logger.error(f"Unexpected error in rate limiter: {str(e)}")
                if attempt < config.max_retries:
                    delay = cls._get_backoff_delay(provider_type, config)
                    time.sleep(delay)
                    priority += 1
                    continue
                raise

    @classmethod
    async def _acquire(
        cls, provider_type: str, config: RateLimitConfig, tokens: int = 0
    ):
        """Acquire rate limits with priority queuing"""
        if not config.enabled:
            return

        priority = cls._consecutive_failures.get(provider_type, 0)

        for attempt in range(config.max_retries + 1):
            try:
                async with cls._lock:
                    now = datetime.now()
                    backoff_until = cls._backoff_until.get(provider_type, now)
                    if now < backoff_until:
                        delay = (backoff_until - now).total_seconds()
                        logger.warning(
                            f"{provider_type}: Global backoff active. Waiting {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)

                    request_limiter, token_limiter, admission_control = (
                        cls.get_limiters(provider_type, config)
                    )

                    # Request admission with current priority
                    await admission_control.admit_request(tokens, priority=priority)

                    # _acquire rate limits
                    timeout = min(30.0, config.max_retry_delay)
                    await request_limiter._acquire(
                        1, timeout=timeout, priority=priority
                    )
                    if tokens > 0:
                        await token_limiter._acquire(
                            tokens, timeout=timeout, priority=priority
                        )

                    cls._consecutive_failures[provider_type] = 0
                    return

            except (RateLimitError, TimeoutError) as e:
                if attempt < config.max_retries:
                    delay = cls._get_backoff_delay(provider_type, config)
                    logger.warning(
                        f"{provider_type}: Rate limit error: {str(e)}, "
                        f"attempt {attempt + 1}/{config.max_retries + 1}. "
                        f"Backing off for {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                    priority += 1  # Increase priority for retries
                    continue
                raise
            except Exception as e:
                logger.error(f"Unexpected error in rate limiter: {str(e)}")
                if attempt < config.max_retries:
                    delay = cls._get_backoff_delay(provider_type, config)
                    await asyncio.sleep(delay)
                    priority += 1
                    continue
                raise

    @classmethod
    def handle_429_sync(cls, provider_type: str, config: RateLimitConfig):
        """Synchronous handling of 429 responses"""
        with cls._sync_lock:
            cls._consecutive_failures[provider_type] = (
                cls._consecutive_failures.get(provider_type, 0) + 1
            )
            failures = cls._consecutive_failures[provider_type]

            if failures > config.max_retries:
                raise RateLimitError(
                    f"Rate limit exceeded and max retries ({config.max_retries}) reached"
                )

            delay = cls._get_backoff_delay(provider_type, config)
            logger.warning(
                f"{provider_type}: 429 received. Setting global backoff for {delay:.2f}s"
            )
            cls._backoff_until[provider_type] = datetime.now() + timedelta(
                seconds=delay
            )
            time.sleep(delay)

    @classmethod
    async def handle_429(cls, provider_type: str, config: RateLimitConfig):
        """Handle 429 with exponential backoff"""
        async with cls._lock:
            cls._consecutive_failures[provider_type] = (
                cls._consecutive_failures.get(provider_type, 0) + 1
            )
            failures = cls._consecutive_failures[provider_type]

            if failures > config.max_retries:
                raise RateLimitError(
                    f"Rate limit exceeded and max retries ({config.max_retries}) reached"
                )

            delay = cls._get_backoff_delay(provider_type, config)
            logger.warning(
                f"{provider_type}: 429 received. Setting global backoff for {delay:.2f}s"
            )
            cls._backoff_until[provider_type] = datetime.now() + timedelta(
                seconds=delay
            )
            await asyncio.sleep(delay)
