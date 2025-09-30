"""
ADK-based API handlers for orchestrator
"""

import os
import uuid
import json
import logging
from typing import Dict, List, Optional
from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from modules.models import A2AMessage, ArtifactData
from modules.orchestrator_core import OrchestratorCore

logger = logging.getLogger(__name__)


class APIHandlers:
    """ADK-based API handlers for orchestrator"""
    
    def __init__(self, orchestrator_core: OrchestratorCore):
        self.orchestrator = orchestrator_core
    
    async def handle_a2a_message(self, message: Dict) -> Dict:
        """Handle A2A protocol messages"""
        try:
            a2a_message = A2AMessage(**message)
            
            # Handle chat requests from frontend
            if a2a_message.message_type == "chat_request":
                chat_content = a2a_message.content
                
                # Prepare chat data for processing
                chat_data = {
                    "session_id": chat_content.get("session_id", str(uuid.uuid4())),
                    "user_id": chat_content.get("user_id", os.getenv('USER_ID', 'anonymous')),
                    "content": chat_content.get("content", ""),
                    "attachments": chat_content.get("attachments", [])
                }
                
                # Analyze and route using ADK workflow
                result = await self.orchestrator.analyze_and_route(
                    chat_data["content"],
                    chat_data["attachments"]
                )
                
                return {
                    "status": "processed",
                    "message_id": a2a_message.id,
                    "result": result
                }
            
            # Handle artifact upload requests
            elif a2a_message.message_type == "artifact_upload":
                artifact_content = a2a_message.content
                session_id = artifact_content.get("session_id", str(uuid.uuid4()))
                
                # Create ArtifactData object
                artifact_data = ArtifactData(
                    filename=artifact_content.get("filename"),
                    mime_type=artifact_content.get("mime_type"),
                    data=artifact_content.get("data"),  # Base64 encoded
                    namespace=artifact_content.get("namespace")
                )
                
                # Handle artifact upload
                result = await self.orchestrator.handle_artifact_upload(artifact_data, session_id)
                
                return {
                    "status": "processed",
                    "message_id": a2a_message.id,
                    "result": result
                }
            
            # Handle agent registration requests
            elif a2a_message.message_type == "agent_registration":
                # Handle agent registration
                await self.orchestrator.handle_agent_registration(a2a_message)
                
                return {
                    "status": "processed",
                    "message_id": a2a_message.id,
                    "result": {"status": "registration_received"}
                }
            else:
                # Handle other A2A message types via ADK
                return {"status": "received", "message_id": a2a_message.id}
                
        except Exception as e:
            logger.error(f"A2A handling error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_agents(self) -> Dict:
        """Get all discovered agents"""
        return {"agents": list(self.orchestrator.agent_registry.values())}
    
    async def get_tasks(self, status: Optional[str] = None) -> Dict:
        """Get tasks with optional status filter"""
        try:
            # Query the database for tasks
            return {"tasks": []}
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_task(self, task_id: str) -> Dict:
        """Get specific task by ID"""
        try:
            # Query the database for specific task
            raise HTTPException(status_code=404, detail="Task not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket endpoint for A2A communication"""
        await websocket.accept()
        client_id = f"client_{id(websocket)}"
        self.orchestrator.websocket_connections[client_id] = websocket
        
        try:
            while True:
                # Receive A2A message from client
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                    
                    # Handle as A2A message
                    result = await self.handle_a2a_message(message_data)
                    
                    # Send response back to client
                    await websocket.send_text(json.dumps(result))
                    
                except json.JSONDecodeError:
                    # Invalid JSON - send error response
                    error_response = {
                        "status": "error",
                        "message": "Invalid JSON format. Please send A2A protocol messages."
                    }
                    await websocket.send_text(json.dumps(error_response))
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket client {client_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Clean up connection
            if client_id in self.orchestrator.websocket_connections:
                del self.orchestrator.websocket_connections[client_id]
    