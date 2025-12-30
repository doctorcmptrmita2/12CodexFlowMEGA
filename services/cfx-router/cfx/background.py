"""
CF-X Background Task Queue Module
Async task queue for best-effort operations (logging, etc.)
"""
import asyncio
import logging
from typing import Callable, Any, Optional
from collections import deque
from uuid import UUID

logger = logging.getLogger(__name__)


class BackgroundTaskQueue:
    """
    Simple async task queue for best-effort operations
    Tasks are executed in background without blocking request handling
    """
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize background task queue
        
        Args:
            max_queue_size: Maximum queue size (drops tasks if full)
        """
        self.queue: deque = deque(maxlen=max_queue_size)
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start background worker"""
        if self.running:
            return
        
        self.running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("Background task queue started")
    
    async def stop(self) -> None:
        """Stop background worker"""
        self.running = False
        if self.worker_task:
            await self.worker_task
        logger.info("Background task queue stopped")
    
    async def enqueue(self, task: Callable, *args, **kwargs) -> bool:
        """
        Enqueue a task for background execution
        
        Args:
            task: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            True if enqueued, False if queue is full
        """
        if len(self.queue) >= self.queue.maxlen:
            logger.warning("Background task queue is full, dropping task")
            return False
        
        self.queue.append((task, args, kwargs))
        return True
    
    async def _worker(self) -> None:
        """Background worker that processes tasks"""
        while self.running:
            try:
                # Wait for tasks with timeout
                if self.queue:
                    task, args, kwargs = self.queue.popleft()
                    try:
                        await task(*args, **kwargs)
                    except Exception as e:
                        # Log error but don't crash worker
                        logger.error(f"Background task failed: {e}", exc_info=True)
                else:
                    # No tasks, sleep briefly
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Background worker error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Back off on error


# Global background task queue instance (singleton)
_background_queue: Optional[BackgroundTaskQueue] = None


def get_background_queue() -> BackgroundTaskQueue:
    """Get global background task queue instance"""
    global _background_queue
    if _background_queue is None:
        _background_queue = BackgroundTaskQueue()
    return _background_queue

