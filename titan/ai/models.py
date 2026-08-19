"""AI Layer Data Models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AIRole(str, Enum):
    """Roles within an AI conversation context."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class PromptContext:
    """Container for snapshot context passed into AI reasoning engines."""

    template_name: str
    system_prompt: str
    user_prompt: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class AIResponse:
    """Structured, immutable response from an AI provider."""

    provider_name: str
    model_name: str
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: Mapping[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
