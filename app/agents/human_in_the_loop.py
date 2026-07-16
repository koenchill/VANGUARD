"""G-013 durable exact-action human-approval protocol.

Every high-consequence tool invocation requires an asymmetric signature over a
canonical digest of the exact action. Nonces are consumed atomically at execution
time. Expired, revoked-key, signature-failure, substitution, replay, concurrent
double-consumption, and store-outage paths all fail closed.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from app.agents.nonce_store import (
    NonceAlreadyConsumedError,
    NonceStore,
    NonceStoreError,
    StoreUnavailableError,
)
from app.agents.signing_service import KmsBackedSigningService, SigningError


class ApprovalRejected(Exception):
    """Fail-closed rejection — action must not execute."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_digest(fields: dict[str, Any]) -> bytes:
    """SHA-256 over canonical JSON of the exact approval field set."""
    required = (
        "actor_id",
        "tenant",
        "mission_id",
        "tool_name",
        "exact_arguments",
        "resource_scope",
        "policy_version",
        "issuance_time",
        "expiration_time",
        "nonce",
    )
    missing = [k for k in required if k not in fields]
    if missing:
        raise ApprovalRejected(f"incomplete approval fields: {missing}")
    payload = {k: fields[k] for k in required}
    # Nested arguments must themselves be canonically ordered.
    payload["exact_arguments"] = json.loads(_canonical_json(payload["exact_arguments"]))
    digest_hex = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return bytes.fromhex(digest_hex)


@dataclass(frozen=True)
class ApprovalRequest:
    actor_id: str
    tenant: str
    mission_id: str
    tool_name: str
    exact_arguments: dict[str, Any]
    resource_scope: str
    policy_version: str
    issuance_time: str
    expiration_time: str
    nonce: str
    digest: bytes

    def as_fields(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "tenant": self.tenant,
            "mission_id": self.mission_id,
            "tool_name": self.tool_name,
            "exact_arguments": self.exact_arguments,
            "resource_scope": self.resource_scope,
            "policy_version": self.policy_version,
            "issuance_time": self.issuance_time,
            "expiration_time": self.expiration_time,
            "nonce": self.nonce,
        }


@dataclass(frozen=True)
class ApprovalToken:
    request: ApprovalRequest
    key_id: str
    signature: bytes


class HumanInTheLoopGate:
    """Approval gate used by supervisor/tools before high-consequence execution."""

    def __init__(
        self,
        signing: KmsBackedSigningService,
        nonce_store: NonceStore,
        *,
        default_ttl_seconds: int = 300,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._signing = signing
        self._nonces = nonce_store
        self._ttl = default_ttl_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create_request(
        self,
        *,
        actor_id: str,
        tenant: str,
        mission_id: str,
        tool_name: str,
        exact_arguments: dict[str, Any],
        resource_scope: str,
        policy_version: str,
        ttl_seconds: int | None = None,
    ) -> ApprovalRequest:
        now = self._clock()
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        nonce = uuid.uuid4().hex
        fields = {
            "actor_id": actor_id,
            "tenant": tenant,
            "mission_id": mission_id,
            "tool_name": tool_name,
            "exact_arguments": exact_arguments,
            "resource_scope": resource_scope,
            "policy_version": policy_version,
            "issuance_time": now.isoformat(),
            "expiration_time": (now + timedelta(seconds=ttl)).isoformat(),
            "nonce": nonce,
        }
        digest = canonical_digest(fields)
        try:
            self._nonces.put_pending(nonce)
        except StoreUnavailableError as exc:
            raise ApprovalRejected("nonce store unavailable at issuance") from exc
        except NonceStoreError as exc:
            raise ApprovalRejected(str(exc)) from exc
        return ApprovalRequest(digest=digest, **fields)  # type: ignore[arg-type]

    def sign_approval(self, request: ApprovalRequest, key_id: str) -> ApprovalToken:
        """Human/approver path — signing happens inside KMS, not app memory."""
        try:
            signature = self._signing.sign(key_id, request.digest)
        except SigningError as exc:
            raise ApprovalRejected(f"signing failed: {exc}") from exc
        return ApprovalToken(request=request, key_id=key_id, signature=signature)

    def authorize_execution(
        self,
        token: ApprovalToken,
        *,
        actor_id: str,
        tenant: str,
        mission_id: str,
        tool_name: str,
        exact_arguments: dict[str, Any],
        resource_scope: str,
        policy_version: str,
    ) -> None:
        """Verify exact-action binding and atomically consume nonce. Fail closed."""
        now = self._clock()
        try:
            exp = datetime.fromisoformat(token.request.expiration_time)
        except ValueError as exc:
            raise ApprovalRejected("malformed expiration_time") from exc
        if now > exp:
            raise ApprovalRejected("approval expired")

        presented = {
            "actor_id": actor_id,
            "tenant": tenant,
            "mission_id": mission_id,
            "tool_name": tool_name,
            "exact_arguments": exact_arguments,
            "resource_scope": resource_scope,
            "policy_version": policy_version,
            "issuance_time": token.request.issuance_time,
            "expiration_time": token.request.expiration_time,
            "nonce": token.request.nonce,
        }
        presented_digest = canonical_digest(presented)
        if presented_digest != token.request.digest:
            raise ApprovalRejected("approval fields do not match signed digest")

        # Detect argument/actor/tool substitution even if caller forged request object.
        if (
            actor_id != token.request.actor_id
            or tenant != token.request.tenant
            or mission_id != token.request.mission_id
            or tool_name != token.request.tool_name
            or _canonical_json(exact_arguments) != _canonical_json(token.request.exact_arguments)
            or resource_scope != token.request.resource_scope
            or policy_version != token.request.policy_version
        ):
            raise ApprovalRejected("actor/tool/argument substitution detected")

        try:
            self._signing.verify(token.key_id, token.request.digest, token.signature)
        except SigningError as exc:
            raise ApprovalRejected(f"signature rejected: {exc}") from exc

        try:
            self._nonces.consume_atomic(token.request.nonce)
        except NonceAlreadyConsumedError as exc:
            raise ApprovalRejected("nonce already consumed (replay)") from exc
        except StoreUnavailableError as exc:
            raise ApprovalRejected("nonce store unavailable") from exc
        except NonceStoreError as exc:
            raise ApprovalRejected(f"nonce consumption failed: {exc}") from exc
