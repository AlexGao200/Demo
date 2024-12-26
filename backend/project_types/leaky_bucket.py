from datetime import datetime
import asyncio
from loguru import logger
import time
import threading
from project_types.error_types import RateLimitError, TimeoutError


class LeakyBucket:
    """Leaky bucket with continuous rate limiting and fair queuing"""

    def __init__(self, rate_per_minute: int, max_queue_size: int = 1000):
        self.rate_per_second = rate_per_minute / 60.0
        self.last_leak = datetime.now()
        self.current_level = 0
        self.max_queue_size = max_queue_size
        self._lock = asyncio.Lock()
        self._sync_lock = threading.Lock()
        self._queue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._dispatcher_task = None
        self._shutdown = False

    async def _leak(self) -> float:
        """Calculate and apply token leakage since last update"""
        now = datetime.now()
        elapsed = (now - self.last_leak).total_seconds()
        leaked = elapsed * self.rate_per_second
        self.current_level = max(0, self.current_level - leaked)
        self.last_leak = now
        return leaked

    def _leak_sync(self) -> float:
        """Calculate and apply token leakage since last update"""
        now = datetime.now()
        elapsed = (now - self.last_leak).total_seconds()
        leaked = elapsed * self.rate_per_second
        self.current_level = max(0, self.current_level - leaked)
        self.last_leak = now
        return leaked

    async def _dispatch_loop(self):
        """Continuously dispatch requests at the configured rate"""
        while not self._shutdown:
            try:
                priority, tokens, future = await self._queue.get()

                try:
                    async with self._lock:
                        await self._leak()

                        # Calculate wait time based on current bucket level
                        if self.current_level > 0:
                            wait_time = self.current_level / self.rate_per_second
                            await asyncio.sleep(wait_time)

                        # Update bucket and complete future
                        self.current_level += tokens
                        if not future.done():
                            future.set_result(None)

                    self._queue.task_done()
                except asyncio.CancelledError:
                    # Ensure we mark the queue item as done even if cancelled
                    self._queue.task_done()
                    raise
                except Exception as e:
                    logger.error(f"Error processing queue item: {e}")
                    self._queue.task_done()
                    if not future.done():
                        future.set_exception(e)

            except asyncio.CancelledError:
                # Clean up any remaining queue items
                while not self._queue.empty():
                    try:
                        _, _, future = self._queue.get_nowait()
                        if not future.done():
                            future.cancel()
                        self._queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                break
            except Exception as e:
                logger.error(f"Error in dispatch loop: {e}")
                await asyncio.sleep(0.1)

    async def _acquire(
        self, tokens: int = 1, timeout: float = 30.0, priority: int = 10
    ):
        """Request tokens with priority queuing"""
        if self._dispatcher_task is None or self._dispatcher_task.done():
            self._shutdown = False
            self._dispatcher_task = asyncio.create_task(self._dispatch_loop())

        future = asyncio.Future()
        try:
            # Add request to priority queue
            await asyncio.wait_for(
                self._queue.put((priority, tokens, future)), timeout=1.0
            )
            # Wait for dispatch
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.CancelledError:
            if not future.done():
                future.cancel()
            # Try to remove our item from the queue if it hasn't been processed
            try:
                # Note: This is a best-effort cleanup
                if not self._queue.empty():
                    self._queue.get_nowait()
                    self._queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                pass
            raise
        except asyncio.TimeoutError:
            if not future.done():
                future.cancel()
            raise TimeoutError(f"Request timed out after {timeout}s")
        except Exception:
            if not future.done():
                future.cancel()
            raise

    def _acquire_sync(self, tokens: int = 1, timeout: float = 30.0, priority: int = 10):
        """Synchronous version of token acquisition with retry logic"""
        if self._shutdown:
            raise RateLimitError("Rate limiter is shut down")

        start_time = time.monotonic()
        while True:
            try:
                with self._sync_lock:
                    # Calculate token leakage
                    self._leak_sync()

                    # Calculate wait time based on current bucket level
                    if self.current_level > 0:
                        wait_time = self.current_level / self.rate_per_second

                        # Check if we would exceed timeout
                        elapsed = time.monotonic() - start_time
                        if elapsed + wait_time > timeout:
                            raise TimeoutError(f"Would exceed timeout of {timeout}s")

                        # Release lock during wait
                        self._sync_lock.release()
                        try:
                            time.sleep(wait_time)
                        finally:
                            self._sync_lock.acquire()

                        # Recalculate after wait
                        self._leak_sync()

                    # Check if we can acquire tokens
                    if (
                        self.current_level + tokens <= self.rate_per_second * 60
                    ):  # Convert to per-minute rate
                        self.current_level += tokens
                        return

                    # Calculate backoff delay based on priority
                    backoff = min(
                        0.1 * (2 ** (priority - 10)), 1.0
                    )  # Exponential backoff starting at 0.1s

                    # Check timeout before backoff
                    elapsed = time.monotonic() - start_time
                    if elapsed + backoff > timeout:
                        raise TimeoutError(f"Would exceed timeout of {timeout}s")

                    # Release lock during backoff
                    self._sync_lock.release()
                    try:
                        time.sleep(backoff)
                    finally:
                        self._sync_lock.acquire()

                    # Increase priority for next attempt
                    priority += 1

            except TimeoutError:
                raise
            except Exception as e:
                if not self._shutdown:
                    logger.error(f"Error in sync token acquisition: {e}")
                    raise

    async def shutdown(self):
        """Gracefully shutdown the dispatcher"""
        self._shutdown = True
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
