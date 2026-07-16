"""KMS/HSM-backed signing service — private keys never enter application memory (G-013).

Application code only ever sees key IDs and signatures. The vault is a separate
process boundary in production; this in-process vault models that isolation for
local tests.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class SigningError(Exception):
    """Fail-closed signing/verification failure."""


class KeyRevokedError(SigningError):
    pass


class KeyNotFoundError(SigningError):
    pass


@dataclass
class _VaultEntry:
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey
    revoked: bool = False


class KmsBackedSigningService:
    """Simulates a dedicated KMS/HSM. Callers never receive private key material."""

    def __init__(self) -> None:
        self._vault: dict[str, _VaultEntry] = {}
        self._lock = threading.Lock()

    def create_key(self, key_id: str) -> bytes:
        """Create a key; returns only the public key bytes."""
        with self._lock:
            if key_id in self._vault:
                raise SigningError(f"key already exists: {key_id}")
            private = Ed25519PrivateKey.generate()
            public = private.public_key()
            self._vault[key_id] = _VaultEntry(private_key=private, public_key=public)
            return public.public_bytes_raw()

    def revoke_key(self, key_id: str) -> None:
        with self._lock:
            entry = self._vault.get(key_id)
            if entry is None:
                raise KeyNotFoundError(key_id)
            entry.revoked = True

    def sign(self, key_id: str, digest: bytes) -> bytes:
        with self._lock:
            entry = self._require(key_id)
            if entry.revoked:
                raise KeyRevokedError(key_id)
            return entry.private_key.sign(digest)

    def verify(self, key_id: str, digest: bytes, signature: bytes) -> None:
        """Raise SigningError on any failure — never return a soft false for revoked keys."""
        with self._lock:
            entry = self._require(key_id)
            if entry.revoked:
                raise KeyRevokedError(key_id)
            try:
                entry.public_key.verify(signature, digest)
            except InvalidSignature as exc:
                raise SigningError("signature verification failed") from exc

    def _require(self, key_id: str) -> _VaultEntry:
        entry = self._vault.get(key_id)
        if entry is None:
            raise KeyNotFoundError(key_id)
        return entry
