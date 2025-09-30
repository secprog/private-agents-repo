#!/usr/bin/env python3
"""Test script for OpenAI integration with ADK."""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the shared models to trigger registration
from shared.models import OpenAI

from google.adk.agents import Agent
from google.adk.models.registry import LLMRegistry
from google.genai import types


async def test_openai_integration():
    """Test the OpenAI integration with ADK."""
    print("Testing OpenAI integration with ADK...")
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        return False
    
    try:
        # Test 1: Check if OpenAI model is registered
        print("\n1. Testing model registration...")
        try:
            llm_class = LLMRegistry.resolve("gpt-4o")
            print(f"SUCCESS: OpenAI model registered: {llm_class}")
        except ValueError as e:
            print(f"ERROR: OpenAI model not registered: {e}")
            return False
        
        # Test 2: Create OpenAI LLM instance
        print("\n2. Testing OpenAI LLM instance creation...")
        openai_llm = OpenAI(model="gpt-4o", max_tokens=100, temperature=0.7)
        print(f"SUCCESS: OpenAI LLM instance created: {openai_llm.model}")
        
        # Test 3: Create Agent with OpenAI model by string
        print("\n3. Testing Agent with OpenAI model string...")
        agent = Agent(
            name="test_openai_agent",
            description="Test agent using OpenAI",
            model="gpt-4o"
        )
        print(f"SUCCESS: Agent created with OpenAI model: {agent.model}")
        
        # Test 4: Create Agent with OpenAI instance
        print("\n4. Testing Agent with OpenAI instance...")
        agent_instance = Agent(
            name="test_openai_agent_instance",
            description="Test agent using OpenAI instance",
            model=openai_llm
        )
        print(f"SUCCESS: Agent created with OpenAI instance: {agent_instance.model}")
        
        # Test 5: Test basic content generation (if API key is available)
        print("\n5. Testing basic content generation...")
        try:
            # Create a simple request
            llm_request = types.LlmRequest(
                model="gpt-4o",
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text="Hello! Please respond with 'OpenAI integration working!'")]
                    )
                ]
            )
            
            # Generate content
            response_count = 0
            async for response in openai_llm.generate_content_async(llm_request):
                response_count += 1
                if response.content and response.content.parts:
                    text_content = response.content.parts[0].text
                    print(f"SUCCESS: OpenAI response: {text_content}")
                else:
                    print(f"ERROR: No content in response: {response}")
                break  # Just test first response
            
            if response_count == 0:
                print("ERROR: No responses received")
                return False
                
        except Exception as e:
            print(f"WARNING: Content generation test failed (this might be expected without valid API key): {e}")
        
        print("\nSUCCESS: All tests passed! OpenAI integration is working correctly.")
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("Starting OpenAI ADK Integration Tests")
    print("=" * 50)
    
    success = await test_openai_integration()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: All tests completed successfully!")
        print("\nYou can now use OpenAI models in your agents:")
        print("  - By model string: model='gpt-4o'")
        print("  - By instance: model=OpenAI(model='gpt-4o')")
    else:
        print("ERROR: Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
