"""Abstract Base Class for AI Providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from titan.ai.models import AIResponse, PromptContext


class AIProvider(ABC):
    """Abstract interface for all TITAN AI language model providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier."""

    @abstractmethod
    def generate(self, context: PromptContext) -> AIResponse:
        """Generate explanation or analysis from prompt context."""
