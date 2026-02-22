"""Provider factory for managing LLM backend instances."""

import logging
from typing import Dict, Optional, Type

from chatbot_ai_system.config import get_settings
from chatbot_ai_system.providers.base import BaseLLMProvider
from chatbot_ai_system.providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating and retrieving LLM providers."""

    _instances: Dict[str, BaseLLMProvider] = {}
    _registry: Dict[str, Type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseLLMProvider]):
        """Register a new provider class."""
        cls._registry[name] = provider_cls

    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """Get or create a provider instance.

        Args:
            provider_name: Name of the provider (e.g., 'ollama', 'openai').
                           If None, uses the default from settings.

        Returns:
            An instance of the requested provider.

        Raises:
            ValueError: If the provider is unknown or not configured.
        """
        settings = get_settings()
        name = provider_name or settings.default_llm_provider

        if name in cls._instances:
            return cls._instances[name]

        if name not in cls._registry:
            # Try to lazy-load optional providers
            if name == "openai":
                from chatbot_ai_system.providers.openai import OpenAIProvider

                cls._registry["openai"] = OpenAIProvider
            elif name == "anthropic":
                from chatbot_ai_system.providers.anthropic import AnthropicProvider

                cls._registry["anthropic"] = AnthropicProvider
            elif name == "gemini":
                from chatbot_ai_system.providers.gemini import GeminiProvider

                cls._registry["gemini"] = GeminiProvider
            else:
                raise ValueError(f"Unknown LLM provider: {name}")

        try:
            provider_cls = cls._registry[name]
            instance = provider_cls()
            cls._instances[name] = instance
            logger.info(f"Initialized LLM provider: {name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to initialize provider {name}: {e}")
            # Fallback to Ollama if default fails?
            # For now, let's allow it to fail explicitly so the user knows config is wrong.
            raise RuntimeError(f"Failed to initialize provider {name}: {e}")
