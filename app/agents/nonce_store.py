"""Durable nonce store with atomic compare-and-delete consumption (G-013)."""

from __future__ import annotations

import threading
from typing import Protocol


class NonceStoreError(Exception):
    """Base store failure — callers must fail closed."""


class StoreUnavailableError(NonceStoreError):
    pass


class NonceAlreadyConsumedError(NonceStoreError):
    pass


class NonceUnknownError(NonceStoreError):
    pass


class NonceStore(Protocol):
    def put_pending(self, nonce: str) -> None: ...

    def consume_atomic(self, nonce: str) -> None:
        """Compare-and-delete. Raises if missing, already consumed, or store down."""


class InMemoryNonceStore:
    """Thread-safe durable-store stand-in for local/unit evidence."""

    def __init__(self) -> None:
        self._pending: set[str] = set()
        self._consumed: set[str] = set()
        self._lock = threading.Lock()
        self.available: bool = True

    def put_pending(self, nonce: str) -> None:
        self._ensure_available()
        with self._lock:
            if nonce in self._pending or nonce in self._consumed:
                raise NonceStoreError(f"nonce already recorded: {nonce}")
            self._pending.add(nonce)

    def consume_atomic(self, nonce: str) -> None:
        self._ensure_available()
        with self._lock:
            if nonce in self._consumed:
                raise NonceAlreadyConsumedError(nonce)
            if nonce not in self._pending:
                raise NonceUnknownError(nonce)
            self._pending.discard(nonce)
            self._consumed.add(nonce)

    def _ensure_available(self) -> None:
        if not self.available:
            raise StoreUnavailableError("approval nonce store unavailable")


class UnavailableNonceStore:
    """Always-outage store for G-013 acceptance (fail closed)."""

    def put_pending(self, nonce: str) -> None:
        raise StoreUnavailableError("approval nonce store unavailable")

    def consume_atomic(self, nonce: str) -> None:
        raise StoreUnavailableError("approval nonce store unavailable")
