#!/usr/bin/env python3
"""Example of modifying the cybersecurity agent to use OpenAI instead of Gemini."""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the shared models to trigger registration
from shared.models import OpenAI

from google.adk.agents import Agent


class CyberSecurityAgentOpenAI:
    """Example cybersecurity agent using OpenAI instead of Gemini."""
    
    def __init__(self):
        self.agent_id = "cybersecurity-agent-openai"
        
        # Initialize ADK LLM agent with OpenAI
        valid_name = self.agent_id.replace("-", "_")
        self.agent = Agent(
            name=valid_name,
            description="Specialized agent for cybersecurity analysis, threat detection, and vulnerability assessment using OpenAI",
            model="gpt-4o"  # Now uses OpenAI instead of Gemini
        )
        
        print(f"SUCCESS: Created cybersecurity agent with OpenAI model: {self.agent.model}")
    
    def get_agent_info(self):
        """Get information about the agent."""
        return {
            "agent_id": self.agent_id,
            "model": self.agent.model,
            "description": self.agent.description,
            "llm_type": type(self.agent.canonical_model).__name__
        }


def main():
    """Main example function."""
    print("Cybersecurity Agent with OpenAI Example")
    print("=" * 50)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY environment variable not set")
        print("The agent will be created but won't be able to make API calls")
        print("Set your API key: export OPENAI_API_KEY='your-key-here'")
        print()
    
    try:
        # Create the agent
        agent = CyberSecurityAgentOpenAI()
        
        # Display agent information
        info = agent.get_agent_info()
        print("Agent Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        print("\nSUCCESS: Cybersecurity agent with OpenAI created successfully!")
        print("\nTo use this agent:")
        print("  1. Set your OPENAI_API_KEY environment variable")
        print("  2. Call agent.agent.run('Your security analysis request')")
        
    except Exception as e:
        print(f"ERROR: Failed to create agent: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
