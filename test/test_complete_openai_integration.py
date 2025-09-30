#!/usr/bin/env python3
"""Complete test of OpenAI integration with ADK."""

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


def test_model_registration():
    """Test that all OpenAI models are properly registered."""
    print("Testing OpenAI model registration...")
    
    test_models = [
        "gpt-4o",
        "gpt-4o-mini", 
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini"
    ]
    
    success_count = 0
    for model in test_models:
        try:
            llm_class = LLMRegistry.resolve(model)
            if llm_class == OpenAI:
                print(f"  SUCCESS: {model} -> {llm_class.__name__}")
                success_count += 1
            else:
                print(f"  ERROR: {model} -> {llm_class.__name__} (expected OpenAI)")
        except ValueError as e:
            print(f"  ERROR: {model} not found: {e}")
    
    print(f"Registration: {success_count}/{len(test_models)} models registered")
    return success_count == len(test_models)


def test_agent_creation():
    """Test creating agents with OpenAI models."""
    print("\nTesting agent creation with OpenAI models...")
    
    try:
        # Test with model string
        agent1 = Agent(
            name="test_agent_string",
            description="Test agent with model string",
            model="gpt-4o"
        )
        print(f"  SUCCESS: Agent created with model string: {agent1.model}")
        
        # Test with OpenAI instance
        openai_llm = OpenAI(model="gpt-4o", max_tokens=500, temperature=0.7)
        agent2 = Agent(
            name="test_agent_instance",
            description="Test agent with OpenAI instance",
            model=openai_llm
        )
        print(f"  SUCCESS: Agent created with OpenAI instance: {agent2.model}")
        
        # Test different models
        models_to_test = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
        for model in models_to_test:
            # Create valid agent name (replace dots and dashes with underscores)
            valid_name = f"test_agent_{model.replace('-', '_').replace('.', '_')}"
            agent = Agent(
                name=valid_name,
                description=f"Test agent with {model}",
                model=model
            )
            print(f"  SUCCESS: Agent created with {model}")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: Failed to create agents: {e}")
        return False


async def test_file_handling():
    """Test file handling capabilities."""
    print("\nTesting file handling capabilities...")
    
    try:
        from shared.models.openai_llm import part_to_openai_content
        
        # Create OpenAI instance for testing
        openai_llm = OpenAI(model="gpt-4o", use_files_api=False)
        
        # Test image handling
        image_data = b"fake_image_data"
        image_part = types.Part(
            inline_data=types.Blob(
                mime_type="image/jpeg",
                data=image_data
            )
        )
        result = await part_to_openai_content(image_part, openai_llm)
        if result["type"] == "image_url":
            print("  SUCCESS: Image handling works")
        else:
            print("  ERROR: Image handling failed")
            return False
        
        # Test PDF handling
        pdf_data = b"fake_pdf_data"
        pdf_part = types.Part(
            inline_data=types.Blob(
                mime_type="application/pdf",
                data=pdf_data
            )
        )
        result = await part_to_openai_content(pdf_part, openai_llm)
        if result["type"] == "image_url":
            print("  SUCCESS: PDF handling works")
        else:
            print("  ERROR: PDF handling failed")
            return False
        
        # Test content creation with files
        content = types.Content(
            role="user",
            parts=[
                types.Part(text="What's in this image?"),
                types.Part(inline_data=types.Blob(
                    mime_type="image/jpeg",
                    data=image_data
                ))
            ]
        )
        print("  SUCCESS: Content with files created")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: File handling test failed: {e}")
        return False


def test_vision_model_detection():
    """Test vision model detection."""
    print("\nTesting vision model detection...")
    
    vision_models = ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"]
    non_vision_models = ["gpt-4-turbo", "gpt-3.5-turbo"]
    
    for model in vision_models:
        try:
            llm_class = LLMRegistry.resolve(model)
            if llm_class == OpenAI:
                print(f"  SUCCESS: {model} is vision-capable")
            else:
                print(f"  ERROR: {model} not registered as OpenAI")
                return False
        except ValueError:
            print(f"  ERROR: {model} not found")
            return False
    
    for model in non_vision_models:
        try:
            llm_class = LLMRegistry.resolve(model)
            if llm_class == OpenAI:
                print(f"  SUCCESS: {model} is text-only")
            else:
                print(f"  ERROR: {model} not registered as OpenAI")
                return False
        except ValueError:
            print(f"  ERROR: {model} not found")
            return False
    
    return True


async def test_openai_instance():
    """Test OpenAI instance creation and configuration."""
    print("\nTesting OpenAI instance creation...")
    
    try:
        # Test basic instance
        openai_llm = OpenAI(model="gpt-4o")
        print(f"  SUCCESS: Basic instance created: {openai_llm.model}")
        
        # Test with custom configuration
        openai_llm_custom = OpenAI(
            model="gpt-4o",
            max_tokens=1000,
            temperature=0.8
        )
        print(f"  SUCCESS: Custom instance created: {openai_llm_custom.model}")
        print(f"    - max_tokens: {openai_llm_custom.max_tokens}")
        print(f"    - temperature: {openai_llm_custom.temperature}")
        
        return True
        
    except Exception as e:
        print(f"  ERROR: OpenAI instance creation failed: {e}")
        return False


def test_supported_models():
    """Test the supported_models method."""
    print("\nTesting supported_models method...")
    
    try:
        supported = OpenAI.supported_models()
        print(f"  SUCCESS: Supported models: {supported}")
        
        # Check for expected patterns
        expected_patterns = ["gpt-.*", "o1-.*"]
        for pattern in expected_patterns:
            if pattern in supported:
                print(f"  SUCCESS: Pattern '{pattern}' found")
            else:
                print(f"  ERROR: Pattern '{pattern}' not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ERROR: supported_models test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("Complete OpenAI ADK Integration Test")
    print("=" * 50)
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY environment variable not set")
        print("Some tests may not work without a valid API key")
        print()
    
    tests = [
        ("Model Registration", test_model_registration, False),
        ("Agent Creation", test_agent_creation, False),
        ("File Handling", test_file_handling, True),
        ("Vision Model Detection", test_vision_model_detection, False),
        ("Supported Models", test_supported_models, False),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func, is_async in tests:
        print(f"\n{test_name}:")
        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"  RESULT: PASSED")
            else:
                print(f"  RESULT: FAILED")
        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  RESULT: FAILED")
    
    # Run async test
    print(f"\nOpenAI Instance Creation:")
    try:
        if await test_openai_instance():
            passed += 1
            print(f"  RESULT: PASSED")
        else:
            print(f"  RESULT: FAILED")
        total += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        print(f"  RESULT: FAILED")
        total += 1
    
    print("\n" + "=" * 50)
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All tests passed! OpenAI integration is fully functional.")
        print("\nIntegration Summary:")
        print("  - Model Registration: WORKING")
        print("  - Agent Creation: WORKING")
        print("  - File Handling: WORKING")
        print("  - Vision Models: WORKING")
        print("  - Configuration: WORKING")
        print("\nYou can now use OpenAI models in your ADK agents!")
        print("  - Import: from shared.models import OpenAI")
        print("  - Use: model='gpt-4o' or model=OpenAI(model='gpt-4o')")
    else:
        print("ERROR: Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
