#!/usr/bin/env python3
"""Test script for OpenAI registration without API calls."""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the shared models to trigger registration
from shared.models import OpenAI

from google.adk.models.registry import LLMRegistry


def test_openai_registration():
    """Test that OpenAI models are properly registered."""
    print("Testing OpenAI model registration...")
    
    # Test different OpenAI model patterns
    test_models = [
        "gpt-4o",
        "gpt-4o-mini", 
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini"
    ]
    
    success_count = 0
    total_count = len(test_models)
    
    for model in test_models:
        try:
            llm_class = LLMRegistry.resolve(model)
            if llm_class == OpenAI:
                print(f"SUCCESS: {model} -> {llm_class.__name__}")
                success_count += 1
            else:
                print(f"ERROR: {model} -> {llm_class.__name__} (expected OpenAI)")
        except ValueError as e:
            print(f"ERROR: {model} not found: {e}")
    
    print(f"\nRegistration test results: {success_count}/{total_count} models registered correctly")
    
    if success_count == total_count:
        print("SUCCESS: All OpenAI models are properly registered!")
        return True
    else:
        print("ERROR: Some models failed to register")
        return False


def test_openai_instance_creation():
    """Test creating OpenAI LLM instances."""
    print("\nTesting OpenAI instance creation...")
    
    try:
        # Test basic instance
        openai_llm = OpenAI(model="gpt-4o")
        print(f"SUCCESS: Basic instance created: {openai_llm.model}")
        
        # Test with custom parameters
        openai_llm_custom = OpenAI(
            model="gpt-4o",
            max_tokens=500,
            temperature=0.8
        )
        print(f"SUCCESS: Custom instance created: {openai_llm_custom.model}")
        print(f"  - max_tokens: {openai_llm_custom.max_tokens}")
        print(f"  - temperature: {openai_llm_custom.temperature}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create OpenAI instances: {e}")
        return False


def test_supported_models():
    """Test the supported_models method."""
    print("\nTesting supported_models method...")
    
    try:
        supported = OpenAI.supported_models()
        print(f"SUCCESS: Supported models patterns: {supported}")
        
        # Check that we have the expected patterns
        expected_patterns = ["gpt-.*", "o1-.*"]
        for pattern in expected_patterns:
            if pattern in supported:
                print(f"SUCCESS: Pattern '{pattern}' found")
            else:
                print(f"ERROR: Pattern '{pattern}' not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to get supported models: {e}")
        return False


def main():
    """Main test function."""
    print("OpenAI ADK Registration Tests")
    print("=" * 40)
    
    tests = [
        test_openai_registration,
        test_openai_instance_creation,
        test_supported_models
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All registration tests passed!")
        print("\nThe OpenAI integration is ready to use.")
        print("To use OpenAI models in your agents:")
        print("  1. Set OPENAI_API_KEY environment variable")
        print("  2. Import shared.models in your code")
        print("  3. Use model='gpt-4o' in your Agent constructors")
    else:
        print("ERROR: Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
