"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional

from chatbot_ai_system.models.schemas import ChatMessage, ChatResponse, StreamChunk


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM provider implementations (Ollama, OpenAI, Anthropic, etc.)
    should inherit from this class and implement its abstract methods.
    """

    provider_name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResponse:
        """Generate a completion for the given messages.

        Args:
            messages: List of chat messages in the conversation
            model: Model to use (uses provider default if not specified)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ChatResponse with the generated message
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a completion for the given messages.

        Args:
            messages: List of chat messages in the conversation
            model: Model to use (uses provider default if not specified)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            StreamChunk objects containing partial content
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and healthy.

        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def get_provider_info(self) -> Dict[str, str]:
        """Get information about this provider.

        Returns:
            Dictionary with provider metadata
        """
        return {
            "name": self.provider_name,
            "models": self.get_available_models(),
        }
