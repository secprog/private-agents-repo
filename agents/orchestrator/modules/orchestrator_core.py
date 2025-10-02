"""
ADK-based Orchestrator core functionality
"""

import os
import json
import uuid
import asyncio
import logging
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime


from modules.models import TaskStatus, A2AMessage, ArtifactData
from modules.session_service import AgentSessionService
from modules.artifact_service import create_artifact_service
from google.adk.agents import Agent

logger = logging.getLogger(__name__)


class OrchestratorCore:
    """ADK-based orchestrator core functionality"""
    
    def __init__(self):
        self.agent_id = "orchestrator-main"
        self.endpoint = os.getenv('ORCHESTRATOR_ENDPOINT', 'https://orchestrator:8000')
        
        # Initialize ADK workflow agent directly
        valid_name = self.agent_id.replace("-", "_")
        self.workflow_agent = Agent(
            name=valid_name,
            description="Master orchestrator for routing tasks to specialized agents",
            model="gemini-2.0-flash"
        )
        
        # Initialize components
        self.session_service = AgentSessionService()
        self.artifact_service = create_artifact_service()
        
        # Agent registry and discovery
        self.agent_registry = {}
        self.discovery_endpoints = self._get_discovery_endpoints()
            
    def _get_discovery_endpoints(self) -> List[str]:
        """Get potential agent endpoints for discovery from environment"""
        endpoints = []
        
        # Get from environment variables - only use what's provided
        for key, value in os.environ.items():
            if key.endswith('_AGENT_ENDPOINT') and value:
                endpoints.append(value)
        
        # If no endpoints provided via env, log warning
        if not endpoints:
            logger.warning("No agent endpoints found in environment variables. Set *_AGENT_ENDPOINT variables.")
        
        return endpoints
    
    async def initialize(self):
        """Initialize orchestrator"""
        try:
            # Initialize Google ADK session service (replaces database)
            # The session service handles its own initialization
            logger.info("Google ADK session service initialized")
            
            
            # Discover available agents first
            await self.discover_agents()
            
            # Start background tasks
            asyncio.create_task(self.periodic_agent_discovery())
            
            logger.info("Orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    
    async def discover_agents(self):
        """Discover available agents and their agent cards using ADK's .well-known/agent-card.json endpoint"""
        logger.info("🔍 Starting dynamic agent discovery...")
        
        for endpoint in self.discovery_endpoints:
            try:
                # Extract agent ID from endpoint (e.g., cybersecurity-agent from https://cybersecurity-agent:8001)
                agent_id = self._extract_agent_id_from_endpoint(endpoint)
                
                # Get agent card from ADK's auto-generated .well-known/agent-card.json endpoint
                agent_card_url = f"{endpoint}/.well-known/agent-card.json"
                
                verify_ssl = os.getenv('VERIFY_SSL', 'true').lower() == 'true'
                async with httpx.AsyncClient(verify=verify_ssl, timeout=10.0) as client:
                    # Try to get agent card first
                    response = await client.get(agent_card_url)
                    if response.status_code == 200:
                        agent_card = response.json()
                        
                        # Store the full agent card with rich metadata
                        self.agent_registry[agent_id] = {
                            "agent_id": agent_id,
                            "endpoint": endpoint,
                            "agent_card": agent_card,  # Store full ADK-generated agent card
                            "capabilities": agent_card.get("capabilities", []),
                            "tools": agent_card.get("tools", []),
                            "description": agent_card.get("description", ""),
                            "version": agent_card.get("version", "1.0.0"),
                            "status": "online"
                        }
                        logger.info(f"✅ Discovered agent {agent_id} at {endpoint} with ADK-generated agent card")
                        logger.debug(f"📋 Agent card: {agent_card}")
                    else:
                        logger.debug(f"❌ No agent card found at {agent_card_url} (status: {response.status_code})")
                    
            except Exception as e:
                logger.debug(f"❌ Agent not available at {endpoint}: {e}")
        
        logger.info(f"🎯 Agent discovery complete. Found {len(self.agent_registry)} agents: {list(self.agent_registry.keys())}")
    
    async def periodic_agent_discovery(self):
        """Periodically discover new agents"""
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            try:
                logger.info("Running periodic agent discovery...")
                await self.discover_agents()
            except Exception as e:
                logger.error(f"Error in periodic agent discovery: {e}")
    
    def _extract_agent_id_from_endpoint(self, endpoint: str) -> str:
        """Extract agent ID from endpoint URL"""
        try:
            # Extract hostname from URL (e.g., cybersecurity-agent from https://cybersecurity-agent:8001)
            from urllib.parse import urlparse
            parsed = urlparse(endpoint)
            hostname = parsed.hostname or parsed.netloc.split(':')[0]
            
            # Convert to agent ID format (e.g., cybersecurity-agent -> cybersecurity-agent-01)
            if '-' in hostname:
                return f"{hostname}-01"
            else:
                return f"{hostname}-agent-01"
        except Exception:
            # Fallback to endpoint-based ID
            return endpoint.replace('https://', '').replace('http://', '').replace(':', '-').replace('/', '-')
    
    
    
    async def handle_agent_card_response(self, message: A2AMessage):
        """Handle agent card response from agents"""
        try:
            agent_card = message.content
            agent_id = agent_card.get("id", message.sender_id)
            
            # Update agent registry with full agent card
            if agent_id in self.agent_registry:
                self.agent_registry[agent_id]["agent_card"] = agent_card
                self.agent_registry[agent_id]["capabilities"] = agent_card.get("capabilities", [])
                self.agent_registry[agent_id]["tools"] = agent_card.get("tools", [])
                self.agent_registry[agent_id]["description"] = agent_card.get("description", "")
                self.agent_registry[agent_id]["version"] = agent_card.get("version", "1.0.0")
                
                logger.info(f"✅ Updated agent card for {agent_id}")
                logger.debug(f"📋 Agent card: {agent_card}")
            else:
                logger.warning(f"⚠️ Received agent card for unknown agent: {agent_id}")
                
        except Exception as e:
            logger.error(f"Error handling agent card response: {e}")
    
    async def find_agent_by_capabilities(self, required_capabilities: List[str]) -> Optional[Dict]:
        """Find the best agent for a task based on agent card capabilities and tools"""
        if not self.agent_registry:
            logger.warning("No agents discovered yet, performing discovery...")
            await self.discover_agents()
        
        best_agent = None
        best_score = 0
        
        for agent_id, agent_info in self.agent_registry.items():
            if agent_info["status"] != "online":
                continue
                
            # Get agent card metadata
            agent_card = agent_info.get("agent_card", {})
            agent_capabilities = agent_info.get("capabilities", [])
            agent_tools = agent_info.get("tools", [])
            agent_description = agent_info.get("description", "")
            
            score = 0
            
            # Check for exact capability matches
            for required_cap in required_capabilities:
                if required_cap in agent_capabilities:
                    score += 10  # High score for exact matches
                elif any(required_cap.lower() in cap.lower() for cap in agent_capabilities):
                    score += 7  # Medium score for partial matches
            
            # Check for tool matches
            for required_cap in required_capabilities:
                for tool in agent_tools:
                    tool_name = tool.get("name", "").lower()
                    tool_desc = tool.get("description", "").lower()
                    if required_cap.lower() in tool_name or required_cap.lower() in tool_desc:
                        score += 8  # High score for tool matches
            
            # Check for semantic matches in description
            for required_cap in required_capabilities:
                if required_cap.lower() in agent_description.lower():
                    score += 3  # Low score for semantic matches
            
            # Bonus for general capabilities
            if any("general" in cap.lower() for cap in agent_capabilities):
                score += 2
            
            if score > best_score:
                best_score = score
                best_agent = agent_info
        
        if best_agent:
            logger.info(f"🎯 Selected agent {best_agent['agent_id']} with score {best_score}")
            logger.debug(f"📋 Agent card: {best_agent.get('agent_card', {})}")
        
        return best_agent
    
    async def handle_artifact_upload(self, artifact_data: ArtifactData, session_id: str) -> Dict:
        """Handle artifact upload and route to appropriate agent"""
        try:
            # Save artifact
            success = self.artifact_service.save_artifact_from_data(artifact_data, session_id)
            if not success:
                return {"status": "error", "message": "Failed to save artifact"}
            
            # Analyze artifact type to determine routing
            analysis = await self._analyze_artifact_type(artifact_data)
            
            # Route to appropriate agent based on analysis
            agent_id = analysis.get("agent_id")
            selected_agent = self.agent_registry.get(agent_id)
            
            if selected_agent and selected_agent.get("status") == "online":
                return await self._route_artifact_to_agent(
                    artifact_data, analysis, agent_id, session_id
                )
            else:
                return {
                    "status": "saved",
                    "artifact": artifact_data.filename,
                    "analysis": analysis,
                    "message": "Artifact saved but no specific agent routing needed"
                }
                
        except Exception as e:
            logger.error(f"Failed to handle artifact upload: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _analyze_artifact_type(self, artifact_data: ArtifactData) -> Dict:
        """Analyze artifact to determine appropriate agent using agent cards"""
        try:
            # Build agent information for LLM analysis
            agent_info = []
            for agent_id, agent_data in self.agent_registry.items():
                agent_card = agent_data.get("agent_card", {})
                agent_info.append({
                    "agent_id": agent_id,
                    "capabilities": agent_data.get("capabilities", []),
                    "tools": [tool.get("name", "") for tool in agent_data.get("tools", [])],
                    "description": agent_data.get("description", "")
                })
            
            # Use LLM to analyze artifact type with rich agent metadata
            analysis_prompt = f"""Analyze this file to determine which agent should handle it.
            Filename: {artifact_data.filename}
            MIME Type: {artifact_data.mime_type}
            
            Available agents with their capabilities and tools:
            {json.dumps(agent_info, indent=2)}
            
            Determine which agent is most appropriate for this file.
            Consider the file type, name, agent capabilities, and tools to make the best match.
            
            Respond with JSON: {{"agent_id": "agent_id", "reason": "explanation"}}
            """
            
            response = await self.agent.run(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Failed to analyze artifact type: {e}")
            return {"error": "Analysis failed", "reason": "LLM analysis failed"}
    
    
    
    async def handle_task_result(self, message: A2AMessage):
        """Handle task result from agent"""
        try:
            task_id = message.content.get("task_id")
            result = message.content.get("result")
            
            # Update task status as session event
            try:
                # Get session for this task
                session = await self.session_service.get_session(
                    app_name="agent_platform",
                    user_id="system",
                    session_id=task_id
                )
                if session:
                    # Append task completion event to session
                    await self.session_service.append_event(session, {
                        "type": "task_completed",
                        "task_id": task_id,
                        "result": result,
                        "completed_by": message.sender_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    logger.info(f"Task {task_id} status updated as session event")
                else:
                    logger.warning(f"Session not found for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to update task status as session event: {e}")
            
            logger.info(f"Task {task_id} completed by {message.sender_id}")
        except Exception as e:
            logger.error(f"Error handling task result: {e}")
    
    async def handle_health_response(self, message: A2AMessage):
        """Handle health check response"""
        try:
            agent_id = message.sender_id
            if agent_id in self.agent_registry:
                self.agent_registry[agent_id]["last_health_check"] = datetime.utcnow().isoformat()
                logger.debug(f"Health check received from {agent_id}")
        except Exception as e:
            logger.error(f"Error handling health response: {e}")
    
    async def handle_capability_response(self, message: A2AMessage):
        """Handle capability response from agent"""
        try:
            agent_id = message.sender_id
            capabilities = message.content.get("capabilities", [])
            if agent_id in self.agent_registry:
                self.agent_registry[agent_id]["capabilities"] = capabilities
                logger.info(f"Updated capabilities for {agent_id}: {capabilities}")
        except Exception as e:
            logger.error(f"Error handling capability response: {e}")
    
    
