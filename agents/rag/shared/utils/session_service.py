"""
Session service using Google ADK DatabaseSessionService with PostgreSQL
"""

import os
import logging
from typing import Dict, List, Optional, Any
from google.adk.sessions import DatabaseSessionService, Session

logger = logging.getLogger(__name__)


class AgentSessionService:
    """Session service using Google ADK DatabaseSessionService with PostgreSQL"""

    def __init__(self):
        # Get database URL from environment
        database_url = os.getenv(
            "DATABASE_URL", "postgresql://admin:admin123@localhost:5432/agent_platform"
        )

        # Initialize Google ADK DatabaseSessionService with PostgreSQL
        self.session_service = DatabaseSessionService(db_url=database_url)

        logger.info("Google ADK DatabaseSessionService initialized with PostgreSQL")

    async def create_session(
        self, app_name: str, user_id: str, initial_state: Optional[Dict] = None
    ) -> Session:
        """Create a new session"""
        session = await self.session_service.create_session(
            app_name=app_name, user_id=user_id, state=initial_state or {}
        )
        logger.info(
            f"Created session {session.id} for user {user_id} in app {app_name}"
        )
        return session

    async def get_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> Optional[Session]:
        """Get an existing session"""
        session = await self.session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        return session

    async def list_sessions(self, app_name: str, user_id: str) -> List[Session]:
        """List all sessions for a user in an app"""
        sessions = await self.session_service.list_sessions(
            app_name=app_name, user_id=user_id
        )
        return sessions

    async def append_event(self, session: Session, event: Any):
        """Append an event to a session"""
        await self.session_service.append_event(session, event)
        logger.debug(f"Appended event to session {session.id}")

    async def delete_session(self, app_name: str, user_id: str, session_id: str):
        """Delete a session"""
        await self.session_service.delete_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        logger.info(f"Deleted session {session_id}")

    async def close(self):
        """Close the session service"""
        # DatabaseSessionService handles connection cleanup automatically
        logger.info("Session service closed")
