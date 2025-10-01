"""
Shared data models for the agent platform
"""

from typing import Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ChatMessage removed - using A2A protocol only


class ArtifactData(BaseModel):
    """Artifact data model for A2A protocol"""
    filename: str
    mime_type: str
    data: str  # Base64 encoded binary data
    version: Optional[int] = None
    namespace: Optional[str] = None  # "user:" prefix for user-scoped artifacts


class A2AMessage(BaseModel):
    """A2A protocol message model"""
    id: str
    sender_id: str
    recipient_id: str
    message_type: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


