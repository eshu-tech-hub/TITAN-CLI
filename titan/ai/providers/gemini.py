"""Google Gemini AI Provider Implementation."""

from __future__ import annotations

import os

from titan.ai.base import AIProvider
from titan.ai.models import AIResponse, PromptContext


class GeminiAIProvider(AIProvider):
    """Google Gemini AI provider implementation using lazy SDK imports."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-3.6-flash",
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        )
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "gemini"

    def generate(self, context: PromptContext) -> AIResponse:
        """Generate an AI response using Google Gemini."""
        if not self._api_key:
            return AIResponse(
                provider_name=self.provider_name,
                model_name=self._model_name,
                content=(
                    "[Gemini Provider Error]: Missing GEMINI_API_KEY. "
                    "Please configure the API key in environment or secrets."
                ),
            )

        try:
            # Lazy import to keep core TITAN independent of google SDK
            from google import genai  # type: ignore[import-untyped]
            from google.genai import types  # type: ignore[import-untyped]

            client = genai.Client(api_key=self._api_key)
            config = types.GenerateContentConfig(
                system_instruction=context.system_prompt,
            )

            response = client.models.generate_content(
                model=self._model_name,
                contents=context.user_prompt,
                config=config,
            )
            
            content_text = response.text if response.text else str(response)

            return AIResponse(
                provider_name=self.provider_name,
                model_name=self._model_name,
                content=content_text,
            )
        except ImportError:
            return AIResponse(
                provider_name=self.provider_name,
                model_name=self._model_name,
                content=(
                    "[Gemini Provider Warning]: 'google-genai' library not installed. "
                    "Install package to enable live Gemini synthesis."
                ),
            )
        except Exception as e:
            return AIResponse(
                provider_name=self.provider_name,
                model_name=self._model_name,
                content=f"[Gemini API Exception]: {e}",
            )


class MockAIProvider(AIProvider):
    """Deterministic mock provider for headless unit testing."""

    def __init__(self, fixed_response: str = "Mock AI Analysis Complete.") -> None:
        self.fixed_response = fixed_response

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(self, context: PromptContext) -> AIResponse:
        return AIResponse(
            provider_name=self.provider_name,
            model_name="mock-v1",
            content=f"{self.fixed_response} (Template: {context.template_name})",
        )
