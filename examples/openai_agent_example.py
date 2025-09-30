#!/usr/bin/env python3
"""Example of using OpenAI with ADK agents."""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the shared models to trigger registration
from shared.models import OpenAI

from google.adk.agents import Agent
from google.genai import types


async def example_openai_agent():
    """Example of creating and using an OpenAI-powered agent."""
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        return
    
    print("🤖 Creating OpenAI-powered agent...")
    
    # Method 1: Using model string (recommended)
    agent = Agent(
        name="openai_agent",
        description="An agent powered by OpenAI GPT models",
        model="gpt-4o"  # This will automatically use our OpenAI implementation
    )
    
    print(f"✅ Agent created with model: {agent.model}")
    
    # Method 2: Using OpenAI instance with custom configuration
    openai_llm = OpenAI(
        model="gpt-4o",
        max_tokens=500,
        temperature=0.7
    )
    
    agent_custom = Agent(
        name="openai_agent_custom",
        description="An agent with custom OpenAI configuration",
        model=openai_llm
    )
    
    print(f"✅ Custom agent created with model: {agent_custom.model}")
    
    # Example of using the agent (this would require actual agent execution)
    print("\n📝 Example usage:")
    print("You can now use these agents in your application:")
    print("  - agent.run('Your message here')")
    print("  - agent_custom.run('Your message here')")
    
    print("\n🔧 Available OpenAI models:")
    print("  - gpt-4o (recommended)")
    print("  - gpt-4o-mini")
    print("  - gpt-4-turbo")
    print("  - gpt-3.5-turbo")
    print("  - o1-preview")
    print("  - o1-mini")


async def example_different_models():
    """Example showing different OpenAI models."""
    
    models_to_test = [
        "gpt-4o",
        "gpt-4o-mini", 
        "gpt-4-turbo",
        "gpt-3.5-turbo"
    ]
    
    print("🔄 Creating agents with different OpenAI models...")
    
    agents = {}
    for model in models_to_test:
        try:
            agent = Agent(
                name=f"agent_{model.replace('-', '_')}",
                description=f"Agent using {model}",
                model=model
            )
            agents[model] = agent
            print(f"✅ Created agent with {model}")
        except Exception as e:
            print(f"❌ Failed to create agent with {model}: {e}")
    
    print(f"\n📊 Successfully created {len(agents)} agents")
    return agents


async def main():
    """Main example function."""
    print("🚀 OpenAI ADK Integration Examples")
    print("=" * 50)
    
    await example_openai_agent()
    print("\n" + "-" * 30)
    await example_different_models()
    
    print("\n" + "=" * 50)
    print("🎉 Examples completed!")
    print("\nNext steps:")
    print("1. Set your OPENAI_API_KEY environment variable")
    print("2. Import shared.models in your agent code")
    print("3. Use OpenAI models in your Agent constructors")


if __name__ == "__main__":
    asyncio.run(main())
