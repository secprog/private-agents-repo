"""
ADK-based Orchestrator core functionality
"""

import os
import logging
import time
import requests
from typing import List, cast

from google.adk.agents import Agent, BaseAgent
from google.adk.agents.remote_a2a_agent import (
    RemoteA2aAgent,
    AGENT_CARD_WELL_KNOWN_PATH,
)
from google.adk.models import LiteLlm

from google.adk.tools import load_memory, preload_memory

# Model constants
LLM_MODEL = os.getenv("LLM_MODEL")

logger = logging.getLogger(__name__)


class OrchestratorCore:
    """ADK-based orchestrator core functionality"""

    def __init__(self):
        self.agent_id = "orchestrator"

        # Initialize ADK workflow agent with basic setup (will be updated after discovery)
        # Use OpenAILLM with memory tools for OpenMemory integration
        self.agent_name = self.agent_id.replace("-", "_")
        self.workflow_agent = Agent(
            name=self.agent_name,
            description="Master orchestrator for routing tasks to specialized agents",
            model=LiteLlm(model="openai/gpt-5-nano"),  # Temporary model before discovery
            instruction="Do nothing, just say: I am discovering available sub-agents...",
            sub_agents=[],
            tools=[preload_memory, load_memory],  # Enable memory tools for OpenMemory
        )

        # Agent registry and discovery
        self.agent_registry = {}
        self.discovery_endpoints = self._get_discovery_endpoints()

        # Initialize synchronously during construction
        self.discover_agents_with_retry()

        # Create workflow agent with discovered sub-agents
        self._create_workflow_agent()

    def _get_discovery_endpoints(self) -> List[str]:
        """Get potential agent endpoints for discovery from environment"""
        endpoints = []

        # Get from environment variables - only use what's provided
        for key, value in os.environ.items():
            if key.endswith("_AGENT_ENDPOINT") and value:
                endpoints.append(value)

        # If no endpoints provided via env, log warning
        if not endpoints:
            logger.warning(
                "No agent endpoints found in environment variables. Set *_AGENT_ENDPOINT variables."
            )

        return endpoints

    def discover_agents_with_retry(self, max_retries: int = 5, retry_delay: int = 5):
        """Discover agents with retry mechanism for startup timing issues"""
        for attempt in range(max_retries):
            logger.info(f"🔍 Agent discovery attempt {attempt + 1}/{max_retries}")

            initial_count = len(self.agent_registry)
            self.discover_agents()
            final_count = len(self.agent_registry)

            if final_count == len(self.discovery_endpoints):
                logger.info(f"✅ All {final_count} agents discovered successfully")
                return
            elif final_count > initial_count:
                logger.info(
                    f"📈 Discovered {final_count - initial_count} new agents, {final_count}/{len(self.discovery_endpoints)} total"
                )

            if attempt < max_retries - 1:
                logger.info(
                    f"⏳ Waiting {retry_delay}s before retry (some agents may still be starting up)"
                )
                time.sleep(retry_delay)

        discovered_count = len(self.agent_registry)
        total_endpoints = len(self.discovery_endpoints)
        if discovered_count < total_endpoints:
            logger.warning(
                f"⚠️ Only discovered {discovered_count}/{total_endpoints} agents after {max_retries} attempts"
            )

    def _create_sub_agents_from_registry(self) -> List[RemoteA2aAgent]:
        """Create RemoteA2aAgent instances from discovered agents"""
        sub_agents = []

        for agent_id, agent_info in self.agent_registry.items():
            try:
                # Create agent card URL using the well-known path
                agent_card_url = f"{agent_info['endpoint']}{AGENT_CARD_WELL_KNOWN_PATH}"

                # Create RemoteA2aAgent - convert name to valid identifier
                valid_name = agent_id.replace(
                    "-", "_"
                )  # Convert hyphens to underscores
                remote_agent = RemoteA2aAgent(
                    name=valid_name,
                    description=agent_info[
                        "description"
                    ],  # Use description from registry
                    agent_card=agent_card_url,
                )

                sub_agents.append(remote_agent)
                logger.info(f"✅ Created sub-agent: {agent_id}")
                logger.info(f"🔗 Sub-agent endpoint: {agent_info['endpoint']}")
                logger.info(
                    f"⚠️  Note: Session context forwarding to RemoteA2aAgent needs verification"
                )
                logger.info(
                    f"🔍 DEBUG: RemoteA2aAgent created with agent_card: {agent_card_url}"
                )

            except Exception as e:
                logger.error(f"Failed to create sub-agent for {agent_id}: {e}")

        return sub_agents

    def _create_workflow_agent(self):
        """Update the workflow agent with discovered sub-agents"""
        try:
            # Create sub-agents from discovered agents
            sub_agents = self._create_sub_agents_from_registry()

            # Build instruction based on discovered agents
            if self.agent_registry:
                instruction = (
                    "You are a dispatcher orchestrator. Analyze the user's request and route it appropriately."
                    + "\n\n"
                    + "IMPORTANT: Never repeat or echo the user's message back to them. Respond directly without restating what they said."
                    + "\n\n"
                    + "ROUTING RULES:"
                    + "\n"
                    + "1. Handle these DIRECTLY without transferring:"
                    + "\n"
                    + "   - Greetings (hello, hi, hey, etc.)"
                    + "\n"
                    + "   - General conversation and small talk"
                    + "\n"
                    + "   - Questions about your capabilities or available agents"
                    + "\n"
                    + "   - Requests for help or clarification"
                    + "\n\n"
                    + "2. TRANSFER to a sub-agent ONLY when the request clearly matches their capabilities:"
                    + "\n"
                    + "   - Vision/image analysis requests → vision_agent"
                    + "\n"
                    + "   - Security analysis requests → cybersecurity_agent"
                    + "\n"
                    + "   - Document/knowledge retrieval → rag_agent"
                    + "\n\n"
                    + "3. If the request is ambiguous or doesn't clearly match any sub-agent:"
                    + "\n"
                    + "   - Ask the user to clarify what they need"
                    + "\n"
                    + "   - Explain the available sub-agents and their capabilities"
                    + "\n"
                    + "   - Do NOT transfer until you understand what they need"
                    + "\n\n"
                    + "When transferring, you may briefly explain that you're routing to a specialized agent."
                    + "\n"
                    + "Do not modify the sub-agent's response, just pass it through to the user."
                    + "\n\n"
                    + "MEMORY CAPABILITIES:"
                    + "\n"
                    + "You have access to memory tools (load_memory, preload_memory) that allow you to remember past conversations and user preferences."
                    + "\n"
                    + "- Use load_memory to search for relevant information from past conversations when needed."
                    + "\n"
                    + "- Use preload_memory to proactively load relevant memories at the start of a conversation."
                    + "\n"
                    + "- This helps you provide better context-aware routing and maintain continuity across sessions."
                )
            else:
                instruction = "Do nothing just say: No specialized sub-agents are currently available."

            # Update the existing workflow agent
            self.workflow_agent.model= LiteLlm(model=LLM_MODEL) # type: ignore
            self.workflow_agent.instruction = instruction
            self.workflow_agent.sub_agents = cast(list[BaseAgent], sub_agents)

            logger.info(f"🤖 Updated workflow agent with {len(sub_agents)} sub-agents")

        except Exception as e:
            logger.error(f"Failed to update workflow agent: {e}")
            # Keep basic instruction as fallback
            self.workflow_agent.instruction = (
                "Do nothing, just say: [FATAL ERROR] Failed to update workflow agent. Please check the logs for more information."
            )
            self.workflow_agent.sub_agents = []

    def discover_agents(self):
        """Discover available agents and their agent cards using ADK's .well-known/agent-card.json endpoint"""
        logger.info("🔍 Starting dynamic agent discovery...")

        for endpoint in self.discovery_endpoints:
            try:
                # Extract agent ID from endpoint (e.g., cybersecurity-agent from http://cybersecurity-agent:8001)
                agent_id = self._extract_agent_id_from_endpoint(endpoint)
                print(f"Agent ID: {agent_id}")
                print(f"Discovery Endpoints: {self.discovery_endpoints}")
                # Use only the ADK standard .well-known/agent-card.json endpoint
                agent_card_url = f"{endpoint}/.well-known/agent-card.json"

                verify_ssl = os.getenv("VERIFY_SSL", "true").lower() == "true"

                try:
                    response = requests.get(
                        agent_card_url, verify=verify_ssl, timeout=10.0
                    )
                    if response.status_code == 200:
                        agent_card = response.json()

                        # Store only essential info - agent exists or it doesn't
                        self.agent_registry[agent_id] = {
                            "endpoint": endpoint,
                            "agent_card": agent_card,
                            "description": agent_card.get(
                                "description", f"Agent {agent_id}"
                            ),
                        }
                        logger.info(f"✅ Discovered agent {agent_id} at {endpoint}")
                        logger.debug(f"📋 Agent card: {agent_card}")
                    else:
                        # Agent not available - remove from registry if it was there
                        if agent_id in self.agent_registry:
                            logger.info(
                                f"❌ Agent {agent_id} no longer available, removing from registry"
                            )
                            del self.agent_registry[agent_id]
                        else:
                            logger.debug(
                                f"❌ No agent card found at {agent_card_url} (status: {response.status_code})"
                            )
                except requests.RequestException as e:
                    logger.debug(f"❌ Request failed for {agent_card_url}: {e}")

            except Exception as e:
                logger.debug(f"❌ Agent not available at {endpoint}: {e}")

        logger.info(
            f"🎯 Agent discovery complete. Found {len(self.agent_registry)} agents: {list(self.agent_registry.keys())}"
        )

    def _extract_agent_id_from_endpoint(self, endpoint: str) -> str:
        """Extract agent ID from endpoint URL"""
        # Extract hostname from URL (e.g., cybersecurity-agent from http://cybersecurity-agent:8001)
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        hostname = parsed.hostname or parsed.netloc.split(":")[0]
        return hostname

    def get_skills_from_sub_agents(self) -> List[dict]:
        """Generate skills list from discovered sub-agents"""
        skills = [
            {
                "id": "orchestration",
                "name": "model",
                "description": self.workflow_agent.instruction,
                "tags": [
                    "llm",
                    "orchestration",
                    "routing",
                    "delegation",
                    "coordination",
                ],
            }
        ]

        # Add skills for each discovered sub-agent
        for agent_id, agent_info in self.agent_registry.items():
            agent_card = agent_info.get("agent_card", {})

            # Extract skills from agent card if available
            agent_skills = agent_card.get("skills", [])

            if agent_skills:
                # Use skills from agent card
                for skill in agent_skills:
                    skill_copy = skill.copy()
                    skill_copy["tags"] = skill_copy.get("tags", []) + [
                        f"sub_agent:{agent_id}"
                    ]
                    skills.append(skill_copy)

        return skills
