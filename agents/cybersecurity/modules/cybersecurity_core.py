"""
ADK-based cybersecurity agent core functionality
"""

import os
import logging

from modules.artifact_service import create_artifact_service
from google.adk.agents import Agent

logger = logging.getLogger(__name__)


class CyberSecurityCore:
    """ADK-based cybersecurity agent core functionality"""
    
    def __init__(self, agent_name: str):
        self.agent_id = agent_name     
        # Initialize ADK LLM agent directly
        valid_name = self.agent_id.replace("-", "_")
        self.agent = Agent(
            name=valid_name,
            description="Specialized agent for cybersecurity",
            model="gemini-2.0-flash",
            instruction="Explain what you received", 
        )
        
        self.artifact_service = create_artifact_service()
    
