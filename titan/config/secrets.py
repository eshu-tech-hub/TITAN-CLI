from __future__ import annotations

import os
from abc import ABC, abstractmethod

from titan.config.exceptions import SecretNotFoundError


class SecretsProvider(ABC):
    """Abstract interface for secret retrieval.

    Implementations can read from environment variables, encrypted
    files, or external vault services (Vault, AWS Secrets Manager,
    Azure Key Vault).
    """

    @abstractmethod
    def get(self, key: str) -> str:
        """Retrieve a secret by its key.

        Raises:
            SecretNotFoundError: If the secret is not available.
        """
        ...

    @abstractmethod
    def get_or_none(self, key: str) -> str | None:
        """Retrieve a secret, returning None if not found."""
        ...


class EnvironmentSecretsProvider(SecretsProvider):
    """Reads secrets from environment variables.

    Environment variable name is derived from the secret key by
    converting to uppercase and replacing dots with underscores,
    optionally prefixed.
    """

    def __init__(self, prefix: str = "TITAN_SECRET") -> None:
        self._prefix = prefix

    def _env_key(self, key: str) -> str:
        parts = [self._prefix, key.upper().replace(".", "_")]
        return "_".join(parts)

    def get(self, key: str) -> str:
        env_key = self._env_key(key)
        value = os.environ.get(env_key)
        if not value:
            raise SecretNotFoundError(
                f"Secret '{key}' not found. Set env var {env_key}."
            )
        return value

    def get_or_none(self, key: str) -> str | None:
        return os.environ.get(self._env_key(key))


class EncryptedFileSecretsProvider(SecretsProvider):
    """Placeholder for encrypted file-based secret storage.

    This implementation always raises SecretNotFoundError.
    It serves as a future integration point for encrypted
    secret files (age, sops, etc.).
    """

    def __init__(self, file_path: str = "") -> None:
        self._file_path = file_path

    def get(self, key: str) -> str:
        raise SecretNotFoundError(
            f"EncryptedFileSecretsProvider is a placeholder. "
            f"Secret '{key}' is not available. "
            f"Configured file: {self._file_path or '(not set)'}"
        )

    def get_or_none(self, key: str) -> str | None:
        return None


class CompositeSecretsProvider(SecretsProvider):
    """Tries multiple secrets providers in order.

    The first provider that returns a non-None value wins.
    """

    def __init__(self, providers: list[SecretsProvider]) -> None:
        self._providers = providers

    def get(self, key: str) -> str:
        for provider in self._providers:
            value = provider.get_or_none(key)
            if value is not None:
                return value
        raise SecretNotFoundError(f"Secret '{key}' not found in any provider")

    def get_or_none(self, key: str) -> str | None:
        for provider in self._providers:
            value = provider.get_or_none(key)
            if value is not None:
                return value
        return None


class InMemorySecretsProvider(SecretsProvider):
    """In-memory secret store for testing."""

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets = dict(secrets or {})

    def get(self, key: str) -> str:
        value = self._secrets.get(key)
        if value is None:
            raise SecretNotFoundError(f"Secret '{key}' not found in memory store")
        return value

    def get_or_none(self, key: str) -> str | None:
        return self._secrets.get(key)

    def set(self, key: str, value: str) -> None:
        self._secrets[key] = value

    def clear(self) -> None:
        self._secrets.clear()
