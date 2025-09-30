"""
Shared data models for the agent platform
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
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


class SecurityAnalysisRequest(BaseModel):
    """Security analysis request model"""
    code: Optional[str] = None
    url: Optional[str] = None
    file_content: Optional[str] = None
    analysis_type: str = "comprehensive"


class ThreatReport(BaseModel):
    """Threat detection report"""
    severity: str  # critical, high, medium, low, info
    threat_type: str
    description: str
    recommendations: List[str]
    confidence: float


class DeploymentRequest(BaseModel):
    """Deployment request model"""
    project_name: str
    environment: str = "development"  # development, staging, production
    deployment_type: str = "docker"  # docker, kubernetes, serverless
    configuration: Optional[Dict] = None


class InfrastructureRequest(BaseModel):
    """Infrastructure request model"""
    action: str  # create, update, destroy
    resource_type: str  # vm, container, database, network
    specifications: Dict
