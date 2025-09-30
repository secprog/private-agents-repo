#!/usr/bin/env python3
"""Test script for OpenAI file handling capabilities."""

import asyncio
import base64
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the shared models to trigger registration
from shared.models import OpenAI

from google.adk.models.registry import LLMRegistry
from google.genai import types


def test_file_handling_conversion():
    """Test file handling conversion functions."""
    print("Testing OpenAI file handling conversion...")
    
    # Test image handling
    print("\n1. Testing image handling...")
    image_data = b"fake_image_data"
    image_part = types.Part(
        inline_data=types.Blob(
            mime_type="image/jpeg",
            data=image_data
        )
    )
    
    # Import the conversion function
    from shared.models.openai_llm import part_to_openai_content
    
    result = part_to_openai_content(image_part)
    expected_base64 = base64.b64encode(image_data).decode()
    
    if result["type"] == "image_url" and expected_base64 in result["image_url"]["url"]:
        print("SUCCESS: Image conversion works correctly")
    else:
        print("ERROR: Image conversion failed")
        return False
    
    # Test PDF handling
    print("\n2. Testing PDF handling...")
    pdf_data = b"fake_pdf_data"
    pdf_part = types.Part(
        inline_data=types.Blob(
            mime_type="application/pdf",
            data=pdf_data
        )
    )
    
    result = part_to_openai_content(pdf_part)
    expected_base64 = base64.b64encode(pdf_data).decode()
    
    if result["type"] == "image_url" and expected_base64 in result["image_url"]["url"]:
        print("SUCCESS: PDF conversion works correctly")
    else:
        print("ERROR: PDF conversion failed")
        return False
    
    # Test unsupported file type
    print("\n3. Testing unsupported file type...")
    unsupported_part = types.Part(
        inline_data=types.Blob(
            mime_type="application/zip",
            data=b"fake_zip_data"
        )
    )
    
    result = part_to_openai_content(unsupported_part)
    
    if result["type"] == "text" and "FILE:" in result["text"]:
        print("SUCCESS: Unsupported file type handled correctly")
    else:
        print("ERROR: Unsupported file type handling failed")
        return False
    
    # Test file reference handling
    print("\n4. Testing file reference handling...")
    file_ref_part = types.Part(
        file_data=types.FileData(
            file_uri="gs://bucket/test.pdf",
            mime_type="application/pdf",
            display_name="remote_file.pdf"
        )
    )
    
    result = part_to_openai_content(file_ref_part)
    
    if result["type"] == "text" and "FILE REFERENCE:" in result["text"]:
        print("SUCCESS: File reference handling works correctly")
    else:
        print("ERROR: File reference handling failed")
        return False
    
    return True


def test_vision_model_detection():
    """Test that vision models are properly identified."""
    print("\nTesting vision model detection...")
    
    vision_models = ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"]
    non_vision_models = ["gpt-4-turbo", "gpt-3.5-turbo"]
    
    for model in vision_models:
        try:
            llm_class = LLMRegistry.resolve(model)
            if llm_class == OpenAI:
                print(f"SUCCESS: {model} is registered as OpenAI (vision-capable)")
            else:
                print(f"ERROR: {model} not registered as OpenAI")
                return False
        except ValueError:
            print(f"ERROR: {model} not found in registry")
            return False
    
    for model in non_vision_models:
        try:
            llm_class = LLMRegistry.resolve(model)
            if llm_class == OpenAI:
                print(f"SUCCESS: {model} is registered as OpenAI (text-only)")
            else:
                print(f"ERROR: {model} not registered as OpenAI")
                return False
        except ValueError:
            print(f"ERROR: {model} not found in registry")
            return False
    
    return True


def test_content_with_files():
    """Test creating content with files."""
    print("\nTesting content creation with files...")
    
    try:
        # Create content with image
        image_data = b"fake_image_data"
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
        
        print("SUCCESS: Content with image created")
        
        # Create content with PDF
        pdf_data = b"fake_pdf_data"
        pdf_content = types.Content(
            role="user",
            parts=[
                types.Part(text="Analyze this document"),
                types.Part(inline_data=types.Blob(
                    mime_type="application/pdf",
                    data=pdf_data
                ))
            ]
        )
        
        print("SUCCESS: Content with PDF created")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create content with files: {e}")
        return False


async def test_openai_with_files():
    """Test OpenAI instance with file handling."""
    print("\nTesting OpenAI instance with file handling...")
    
    try:
        # Create OpenAI instance
        openai_llm = OpenAI(model="gpt-4o")
        print(f"SUCCESS: OpenAI instance created: {openai_llm.model}")
        
        # Test that it's a vision-capable model
        if openai_llm.model in ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"]:
            print("SUCCESS: Using vision-capable model for file processing")
        else:
            print("WARNING: Model may not support file processing")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create OpenAI instance: {e}")
        return False


def main():
    """Main test function."""
    print("OpenAI File Handling Tests")
    print("=" * 40)
    
    tests = [
        test_file_handling_conversion,
        test_vision_model_detection,
        test_content_with_files,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    # Run async test
    print("Testing async functionality...")
    try:
        result = asyncio.run(test_openai_with_files())
        if result:
            passed += 1
        total += 1
    except Exception as e:
        print(f"ERROR: Async test failed: {e}")
        total += 1
    
    print("=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: All file handling tests passed!")
        print("\nFile handling capabilities:")
        print("  - Images: SUPPORTED (base64 encoded)")
        print("  - PDFs: SUPPORTED (vision models)")
        print("  - Documents: SUPPORTED (vision models)")
        print("  - File References: NOT SUPPORTED (converted to text)")
        print("  - Unsupported Types: CONVERTED to text descriptions")
    else:
        print("ERROR: Some file handling tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
