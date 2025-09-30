"""Shared models for the agent platform."""

from .openai_llm import OpenAI
from . import registry  # This will auto-register the models

__all__ = ["OpenAI"]
