from __future__ import annotations


class AuditError(Exception):
    """Base exception for audit framework errors."""


class EventValidationError(AuditError):
    """Audit event failed validation."""


class StorageError(AuditError):
    """Audit storage operation failed."""


class IntegrityError(AuditError):
    """Integrity verification failed."""


class QueryError(AuditError):
    """Audit query execution failed."""


class SequenceError(AuditError):
    """Sequence number assignment failed."""


class HashChainError(IntegrityError):
    """Hash chain verification failed."""
