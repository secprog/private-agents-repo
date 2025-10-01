"""
Shared data models for the agent platform
"""

from typing import Dict, Optional, Any
from pydantic import BaseModel


# ChatMessage removed - using A2A protocol only


class A2AMessage(BaseModel):
    """A2A protocol message model"""
    id: str
    sender_id: str
    recipient_id: str
    message_type: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None




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
