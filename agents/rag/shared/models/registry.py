"""Registry setup for custom LLM models."""

from google.adk.models.registry import LLMRegistry
from .openai_llm import OpenAI


def register_custom_models():
    """Register custom LLM models with the ADK registry."""
    # Register OpenAI models
    for regex in OpenAI.supported_models():
        LLMRegistry._register(regex, OpenAI)

    print("Custom LLM models registered successfully")


# Auto-register when module is imported
register_custom_models()
