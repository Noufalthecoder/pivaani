import asyncio
import hashlib
import logging
from typing import Dict, Optional

logger = logging.getLogger("pivaani.locks")

class IdempotencyLockManager:
    """
    In-memory async distributed lock manager preventing race conditions
    and double-spend attacks in high-concurrency payment retaps and approvals.
    """

    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
        self._meta_lock = asyncio.Lock()

    @staticmethod
    def generate_key(identifier: str, action_type: str = "default") -> str:
        """Produces a deterministic idempotency key string"""
        raw = f"{identifier}:{action_type}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def acquire(self, key: str) -> bool:
        """
        Attempts to acquire the lock for the given key without blocking.
        Returns True if the lock was successfully acquired.
        Returns False if the lock is already held by an in-flight operation.
        """
        async with self._meta_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            lock = self._locks[key]

            # If the lock is already held, reject immediately
            if lock.locked():
                logger.warning(f"🔒 Concurrency lock collision for key {key[:12]}... (already held)")
                return False

            # Lock is free: acquire it
            await lock.acquire()
            logger.debug(f"🔑 Acquired lock for key {key[:12]}...")
            return True

    def lock_for(self, key: str) -> asyncio.Lock:
        """Blocking variant: `async with lock_manager.lock_for(key)` serializes callers instead of rejecting them"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def release(self, key: str):
        """
        Releases the lock for the given key if currently held.
        """
        if key in self._locks:
            lock = self._locks[key]
            if lock.locked():
                try:
                    lock.release()
                    logger.debug(f"🔓 Released lock for key {key[:12]}...")
                except RuntimeError as e:
                    logger.warning(f"Error releasing lock for key {key[:12]}: {e}")

# Global singleton lock manager
lock_manager = IdempotencyLockManager()

async def acquire(key: str) -> bool:
    """Utility wrapper for lock_manager.acquire"""
    return await lock_manager.acquire(key)

def release(key: str):
    """Utility wrapper for lock_manager.release"""
    lock_manager.release(key)

