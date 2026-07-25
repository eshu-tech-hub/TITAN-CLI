from __future__ import annotations

import hashlib
import json
from typing import Any

from titan.audit.exceptions import EventValidationError
from titan.audit.models import (
    AuditCategory,
    AuditEvent,
    AuditResult,
    AuditSeverity,
    AuditSource,
)


def compute_event_hash(event: AuditEvent) -> str:
    """Compute SHA-256 hash of an audit event for integrity verification.

    The hash covers all core fields except ``event_hash`` itself.
    ``previous_hash`` IS included to form the hash chain.
    The serialized payload is canonical (sorted keys, deterministic JSON)
    so the same event always produces the same hash.
    """
    payload = _hash_payload(event)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_event_hash_from_dict(data: dict[str, Any]) -> str:
    """Compute SHA-256 hash from a pre-serialized dictionary.

    Only ``event_hash`` is excluded to match :func:`_hash_payload`
    which includes all other fields (including ``previous_hash``).
    """
    filtered = {k: v for k, v in sorted(data.items()) if k != "event_hash"}
    payload = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_event(event: AuditEvent) -> list[str]:
    """Validate an audit event and return a list of error messages.

    An empty list means the event is valid.
    """
    errors: list[str] = []

    if not event.event_id:
        errors.append("event_id must not be empty")

    if not event.action:
        errors.append("action must not be empty")

    if event.sequence_number < 0:
        errors.append("sequence_number must be non-negative")

    if event.timestamp.tzinfo is None:
        errors.append("timestamp must be timezone-aware (UTC)")

    return errors


def create_audit_event(
    *,
    source: AuditSource,
    category: AuditCategory,
    severity: AuditSeverity,
    action: str,
    result: AuditResult = AuditResult.SUCCESS,
    sequence_number: int = 0,
    correlation_id: str = "",
    pipeline_id: str = "",
    trade_id: str = "",
    order_id: str = "",
    position_id: str = "",
    runtime_id: str = "",
    user_id: str = "",
    previous_hash: str = "",
    metadata: dict[str, Any] | None = None,
    event_id: str = "",
) -> AuditEvent:
    """Factory for creating validated AuditEvent instances.

    Generates a UUID-based event_id if not supplied, sets the
    timestamp to current UTC, and computes the event hash.
    """
    import uuid
    from datetime import datetime, timezone

    if not event_id:
        event_id = str(uuid.uuid4())

    event = AuditEvent(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        sequence_number=sequence_number,
        source=source,
        category=category,
        severity=severity,
        action=action,
        result=result,
        correlation_id=correlation_id,
        pipeline_id=pipeline_id,
        trade_id=trade_id,
        order_id=order_id,
        position_id=position_id,
        runtime_id=runtime_id,
        user_id=user_id,
        previous_hash=previous_hash,
        metadata=metadata or {},
    )

    errors = validate_event(event)
    if errors:
        raise EventValidationError(f"Event validation failed: {'; '.join(errors)}")

    event_hash = compute_event_hash(event)

    return AuditEvent(
        event_id=event.event_id,
        timestamp=event.timestamp,
        sequence_number=event.sequence_number,
        source=event.source,
        category=event.category,
        severity=event.severity,
        action=event.action,
        result=event.result,
        correlation_id=event.correlation_id,
        pipeline_id=event.pipeline_id,
        trade_id=event.trade_id,
        order_id=event.order_id,
        position_id=event.position_id,
        runtime_id=event.runtime_id,
        user_id=event.user_id,
        event_hash=event_hash,
        previous_hash=previous_hash,
        metadata=event.metadata,
    )


def _hash_payload(event: AuditEvent) -> str:
    """Build canonical JSON payload for hashing."""
    data = {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
        "sequence_number": event.sequence_number,
        "source": event.source.value,
        "category": event.category.value,
        "severity": event.severity.value,
        "action": event.action,
        "result": event.result.value,
        "correlation_id": event.correlation_id,
        "pipeline_id": event.pipeline_id,
        "trade_id": event.trade_id,
        "order_id": event.order_id,
        "position_id": event.position_id,
        "runtime_id": event.runtime_id,
        "user_id": event.user_id,
        "previous_hash": event.previous_hash,
        "metadata": event.metadata,
    }
    return json.dumps(data, sort_keys=True, default=str)
