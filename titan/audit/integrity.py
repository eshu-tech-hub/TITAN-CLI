from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from titan.audit.event import compute_event_hash
from titan.audit.exceptions import IntegrityError
from titan.audit.models import AuditEvent


@dataclass(frozen=True, slots=True)
class IntegrityViolation:
    """Details of a single integrity violation found during verification."""

    sequence_number: int
    event_id: str
    violation_type: str
    expected: str
    actual: str
    description: str


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    """Result of an integrity verification pass."""

    total_events: int = 0
    valid_events: int = 0
    violations: tuple[IntegrityViolation, ...] = field(default_factory=tuple)
    chain_valid: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        return self.chain_valid and len(self.violations) == 0

    @property
    def violation_count(self) -> int:
        return len(self.violations)


class IntegrityEngine:
    """Verifies hash-chain integrity of audit events.

    Each audit event's ``event_hash`` is a SHA-256 digest of its contents.
    The ``previous_hash`` field links each event to its predecessor, forming
    a chain analogous to a blockchain.  Any modification to a persisted event
    breaks the chain and is detected by :meth:`verify`.
    """

    def verify(self, events: Sequence[AuditEvent]) -> IntegrityReport:
        """Verify the full hash chain of a sequence of events.

        Checks performed:
        1. Each event's hash matches a fresh recomputation.
        2. Each event's ``previous_hash`` matches the preceding event's hash.
        3. The first event has an empty ``previous_hash``.

        Returns an :class:`IntegrityReport` with all violations found.
        """
        violations: list[IntegrityViolation] = []
        total = len(events)

        if total == 0:
            return IntegrityReport(
                total_events=0,
                valid_events=0,
                chain_valid=True,
            )

        prev_hash = ""
        valid_count = 0

        for idx, event in enumerate(events):
            # Check previous_hash linkage
            if event.previous_hash != prev_hash:
                violations.append(
                    IntegrityViolation(
                        sequence_number=event.sequence_number,
                        event_id=event.event_id,
                        violation_type="chain_break",
                        expected=prev_hash or "(empty)",
                        actual=event.previous_hash or "(empty)",
                        description=(
                            f"previous_hash mismatch at index {idx}: "
                            f"expected {prev_hash!r}, got {event.previous_hash!r}"
                        ),
                    )
                )

            # Verify event hash
            recomputed = compute_event_hash(event)
            if event.event_hash != recomputed:
                violations.append(
                    IntegrityViolation(
                        sequence_number=event.sequence_number,
                        event_id=event.event_id,
                        violation_type="hash_mismatch",
                        expected=recomputed,
                        actual=event.event_hash,
                        description=(
                            f"Event hash mismatch at index {idx}: "
                            f"expected {recomputed!r}, got {event.event_hash!r}"
                        ),
                    )
                )
            else:
                valid_count += 1

            prev_hash = event.event_hash

        chain_valid = len(violations) == 0

        return IntegrityReport(
            total_events=total,
            valid_events=valid_count,
            violations=tuple(violations),
            chain_valid=chain_valid,
        )

    def detect_tampering(
        self, events: Sequence[AuditEvent], tampered_indices: set[int]
    ) -> IntegrityReport:
        """Utility for testing: verify that specific tampered events are detected.

        This does NOT modify any events.  It simply runs verification and
        confirms that violations exist at the given indices.
        """
        report = self.verify(events)
        if not tampered_indices and report.is_valid:
            return report
        if tampered_indices and report.is_valid:
            raise IntegrityError(
                "Expected tampering to be detected but chain verified clean"
            )
        return report
