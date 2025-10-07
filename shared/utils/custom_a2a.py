"""
Custom A2A server creation with database session service
"""

import logging
from typing import Optional
from fastapi import FastAPI

# Monkey patch the runner creation in the to_a2a function
# This is a bit hacky but necessary since to_a2a doesn't expose service configuration
import google.adk.a2a.utils.agent_to_a2a as agent_to_a2a_module
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.auth.credential_service.base_credential_service import BaseCredentialService
from google.adk.artifacts.base_artifact_service import BaseArtifactService
from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions import DatabaseSessionService
from a2a.types import AgentCard

logger = logging.getLogger(__name__)

def create_database_session_service() -> DatabaseSessionService:
    """Create a database session service instance for Docker containers"""
    import os
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://admin:admin123@localhost:5432/agent_platform')
    
    # Initialize Google ADK DatabaseSessionService with PostgreSQL
    session_service = DatabaseSessionService(db_url=database_url)
    
    logger.info(f"DatabaseSessionService initialized with PostgreSQL: {database_url}")
    return session_service

def create_a2a_server_with_shared_session(
    agent: Agent,
    port: int = 8001,
    host: str = "0.0.0.0",
    protocol: str = "http",
    agent_card: Optional[AgentCard] = None,
    session_service: Optional[BaseSessionService] = None,
    artifact_service: Optional[BaseArtifactService] = InMemoryArtifactService(),
    memory_service: Optional[BaseMemoryService] = InMemoryMemoryService(),
    credential_service: Optional[BaseCredentialService] = InMemoryCredentialService(),
    **kwargs
) -> FastAPI:
    """
    Create an A2A server with database session service.
    
    This function creates an A2A server that uses the Services
    instead of the default InMemoryServices, ensuring consistency
    across all agents.
    """
    # Use database session service if none provided
    if session_service is None:
        session_service = create_database_session_service()
    
    # Create a custom runner that uses the custom service
    def create_runner() -> Runner:
        """Create a runner with session services."""
        return Runner(
            app_name=agent.name or "adk_agent",
            agent=agent,
            # Use services instead of InMemoryServices
            artifact_service=artifact_service,
            session_service=session_service,
            memory_service=memory_service,
            credential_service=credential_service,
        )
    
    # Replace with our custom function
    agent_to_a2a_module._create_runner = create_runner
    # Create the A2A server
    app = to_a2a(
        agent=agent,
        port=port,
        host=host,
        protocol=protocol,
        agent_card=agent_card,
        **kwargs
    )
    
    logger.info("✅ Created A2A server with proper services")
    logger.info(f"🔧 Session service type: {type(session_service)}")
    logger.info(f"🔧 Artifact service type: {type(artifact_service)}")
    logger.info(f"🔧 Agent name: {agent.name}")
    return app
