from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from loguru import logger
from collections import deque
import time
import threading
import queue
from project_types.error_types import RateLimitError, TimeoutError


@dataclass
class TokenUsage:
    """Track token usage with timestamps"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class QueueItem:
    """Wrapper for queue items to ensure proper comparison"""

    priority: int
    tokens: int
    future: asyncio.Future
    timestamp: float = field(default_factory=time.monotonic)

    def __lt__(self, other):
        if not isinstance(other, QueueItem):
            return NotImplemented
        # First compare by priority, then by timestamp for FIFO behavior
        return (self.priority, self.timestamp) < (other.priority, other.timestamp)


class RequestAdmissionControl:
    """Advanced admission control with fair queuing"""

    def __init__(self, max_requests_per_minute: int, max_tokens_per_minute: int):
        self.max_requests = max_requests_per_minute
        self.max_tokens = max_tokens_per_minute
        self.requests = deque()
        self.token_usage = deque()
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()  # Added for sync operations
        self._queue = asyncio.PriorityQueue(maxsize=1000)
        self._sync_queue = queue.PriorityQueue(maxsize=1000)
        self._dispatcher_task = None
        self._shutdown = False

    def _clean_old_records(self, now: datetime):
        """Remove records older than 60 seconds"""
        cutoff = now - timedelta(seconds=60)
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        while self.token_usage and self.token_usage[0][0] < cutoff:
            self.token_usage.popleft()

    async def _dispatch_loop(self):
        """Fair request dispatcher"""
        while not self._shutdown:
            try:
                queue_item: QueueItem = await self._queue.get()

                async with self._lock:
                    now = datetime.now()
                    self._clean_old_records(now)

                    # Calculate available capacity
                    available_requests = self.max_requests - len(self.requests)
                    current_tokens = sum(
                        usage.total_tokens for _, usage in self.token_usage
                    )
                    available_tokens = self.max_tokens - current_tokens

                    if available_requests > 0 and (
                        queue_item.tokens == 0 or available_tokens >= queue_item.tokens
                    ):
                        self.requests.append(now)
                        if queue_item.tokens > 0:
                            usage = TokenUsage(
                                input_tokens=queue_item.tokens,
                                total_tokens=queue_item.tokens,
                            )
                            self.token_usage.append((now, usage))
                        if not queue_item.future.done():
                            queue_item.future.set_result(None)
                    else:
                        # Re-queue with backoff if capacity not available
                        await asyncio.sleep(0.1)
                        if not self._shutdown:
                            new_item = QueueItem(
                                priority=queue_item.priority + 1,
                                tokens=queue_item.tokens,
                                future=queue_item.future,
                            )
                            await self._queue.put(new_item)

                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in admission control dispatch: {e}")
                await asyncio.sleep(0.1)

    async def can_admit_request(self, tokens: int = 0) -> bool:
        """Check if a new request can be admitted"""
        async with self._lock:
            now = datetime.now()
            self._clean_old_records(now)

            if len(self.requests) >= self.max_requests:
                return False

            if tokens > 0:
                current_tokens = sum(
                    usage.total_tokens for _, usage in self.token_usage
                )
                if current_tokens + tokens > self.max_tokens:
                    return False

            return True

    def can_admit_request_sync(self, tokens: int = 0) -> bool:
        """Check if a new request can be admitted"""
        with self._sync_lock:
            now = datetime.now()
            self._clean_old_records(now)

            if len(self.requests) >= self.max_requests:
                return False

            if tokens > 0:
                current_tokens = sum(
                    usage.total_tokens for _, usage in self.token_usage
                )
                if current_tokens + tokens > self.max_tokens:
                    return False

            return True

    async def admit_request(
        self, tokens: int = 0, priority: int = 10, timeout: float = 30.0
    ):
        """Request admission with priority queuing"""
        if self._dispatcher_task is None or self._dispatcher_task.done():
            self._shutdown = False
            self._dispatcher_task = asyncio.create_task(self._dispatch_loop())

        future = asyncio.Future()
        queue_item = QueueItem(priority=priority, tokens=tokens, future=future)

        try:
            await asyncio.wait_for(self._queue.put(queue_item), timeout=1.0)
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            if not future.done():
                future.cancel()
            raise TimeoutError(f"Admission request timed out after {timeout}s")
        except Exception:
            if not future.done():
                future.cancel()
            raise

    def admit_request_sync(
        self, tokens: int = 0, priority: int = 10, timeout: float = 30.0
    ):
        """Synchronous version of request admission with retry logic"""
        if self._shutdown:
            raise RateLimitError("Admission control is shut down")

        start_time = time.monotonic()
        while True:
            try:
                with self._sync_lock:
                    now = datetime.now()
                    self._clean_old_records(now)

                    # Calculate available capacity
                    available_requests = self.max_requests - len(self.requests)
                    current_tokens = sum(
                        usage.total_tokens for _, usage in self.token_usage
                    )
                    available_tokens = self.max_tokens - current_tokens

                    # Check if we can admit
                    if available_requests > 0 and (
                        tokens == 0 or available_tokens >= tokens
                    ):
                        # Record the request
                        self.requests.append(now)
                        if tokens > 0:
                            usage = TokenUsage(
                                input_tokens=tokens,
                                total_tokens=tokens,
                            )
                            self.token_usage.append((now, usage))
                        return

                    # Check timeout
                    elapsed = time.monotonic() - start_time
                    if elapsed > timeout:
                        raise TimeoutError(f"Request timed out after {timeout}s")

                    # Calculate backoff delay based on priority
                    backoff = min(
                        0.1 * (2 ** (priority - 10)), 1.0
                    )  # Exponential backoff starting at 0.1s

                    # Release lock during backoff
                    time.sleep(backoff)

                    # Increase priority for next attempt
                    priority += 1

            except TimeoutError:
                raise
            except Exception as e:
                if not self._shutdown:
                    logger.error(f"Error in sync admission control: {e}")
                    raise

    def add_usage_sync(self, input_tokens: int = 0, output_tokens: int = 0):
        """Record token usage for an admitted request"""
        with self._sync_lock:  # Use threading.Lock for sync operations
            now = datetime.now()
            self._clean_old_records(now)

            current_tokens = sum(usage.total_tokens for _, usage in self.token_usage)
            new_tokens = input_tokens + output_tokens

            if current_tokens + new_tokens > self.max_tokens:
                raise RateLimitError("Token usage would exceed rate limit")

            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=new_tokens,
            )
            self.token_usage.append((now, usage))

    async def add_usage(self, input_tokens: int = 0, output_tokens: int = 0):
        """Record token usage for an admitted request"""
        async with self._lock:
            now = datetime.now()
            self._clean_old_records(now)

            current_tokens = sum(usage.total_tokens for _, usage in self.token_usage)
            new_tokens = input_tokens + output_tokens

            if current_tokens + new_tokens > self.max_tokens:
                raise RateLimitError("Token usage would exceed rate limit")

            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=new_tokens,
            )
            self.token_usage.append((now, usage))

    async def shutdown(self):
        """Gracefully shutdown the dispatcher"""
        self._shutdown = True
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
