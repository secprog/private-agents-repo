#!/usr/bin/env python3
"""Example of using OpenAI Files API with ADK agents."""

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


async def example_files_api_usage():
    """Example of using OpenAI Files API with ADK agents."""
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY environment variable not set")
        print("The agent will be created but won't be able to make API calls")
        print("Set your API key: export OPENAI_API_KEY='your-key-here'")
        print()
    
    print("OpenAI Files API Example")
    print("=" * 40)
    
    # Example 1: Agent with Files API enabled (default)
    print("\n1. Creating agent with Files API enabled...")
    agent_with_files_api = Agent(
        name="agent_with_files_api",
        description="Agent that uploads documents to OpenAI Files API",
        model="gpt-4o"  # Vision-capable model required for file processing
    )
    print(f"SUCCESS: Agent created with model: {agent_with_files_api.model}")
    
    # Example 2: Agent with Files API disabled (base64 only)
    print("\n2. Creating agent with Files API disabled...")
    openai_llm_no_files_api = OpenAI(
        model="gpt-4o",
        use_files_api=False  # Disable Files API, use base64 only
    )
    agent_no_files_api = Agent(
        name="agent_no_files_api",
        description="Agent that uses base64 encoding for all files",
        model=openai_llm_no_files_api
    )
    print(f"SUCCESS: Agent created with Files API disabled")
    
    # Example 3: Creating content with different file types
    print("\n3. Creating content with different file types...")
    
    # Image content (always uses base64)
    image_data = b"fake_image_data"
    image_content = types.Content(
        role="user",
        parts=[
            types.Part(text="What's in this image?"),
            types.Part(inline_data=types.Blob(
                mime_type="image/jpeg",
                data=image_data,
                display_name="sample_image.jpg"
            ))
        ]
    )
    print("SUCCESS: Image content created")
    
    # PDF content (will be uploaded to Files API if enabled)
    pdf_data = b"fake_pdf_content"
    pdf_content = types.Content(
        role="user",
        parts=[
            types.Part(text="Please analyze this document:"),
            types.Part(inline_data=types.Blob(
                mime_type="application/pdf",
                data=pdf_data,
                display_name="sample_document.pdf"
            ))
        ]
    )
    print("SUCCESS: PDF content created")
    
    # Document content (will be uploaded to Files API if enabled)
    doc_data = b"fake_document_content"
    doc_content = types.Content(
        role="user",
        parts=[
            types.Part(text="Review this document:"),
            types.Part(inline_data=types.Blob(
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                data=doc_data,
                display_name="sample_document.docx"
            ))
        ]
    )
    print("SUCCESS: Document content created")
    
    # Example 4: File reference handling
    print("\n4. Creating content with file references...")
    file_ref_content = types.Content(
        role="user",
        parts=[
            types.Part(text="Please process this file:"),
            types.Part(file_data=types.FileData(
                file_uri="gs://bucket/sample.pdf",
                mime_type="application/pdf",
                display_name="remote_document.pdf"
            ))
        ]
    )
    print("SUCCESS: File reference content created")
    
    print("\n" + "=" * 40)
    print("Files API Configuration Summary:")
    print("  - Files API Enabled: Documents uploaded to OpenAI Files API")
    print("  - Files API Disabled: All files converted to base64")
    print("  - Images: Always use base64 encoding")
    print("  - File References: Converted to text descriptions")
    print("\nFile Processing Flow:")
    print("  1. Images -> Base64 encoding")
    print("  2. PDFs/Documents -> Files API upload (if enabled) or Base64")
    print("  3. File References -> Text descriptions")
    print("  4. Unsupported Types -> Text descriptions")
    
    print("\nTo use these agents:")
    print("  1. Set your OPENAI_API_KEY environment variable")
    print("  2. Call agent.run('Your message with files')")
    print("  3. Files will be automatically processed according to configuration")


async def example_file_handling_comparison():
    """Example comparing different file handling approaches."""
    
    print("\nFile Handling Comparison")
    print("=" * 40)
    
    # Create test file data
    test_pdf_data = b"fake_pdf_content"
    test_image_data = b"fake_image_content"
    
    # Test with Files API enabled
    print("\n1. Testing with Files API enabled...")
    openai_with_files = OpenAI(model="gpt-4o", use_files_api=True)
    
    pdf_part = types.Part(
        inline_data=types.Blob(
            mime_type="application/pdf",
            data=test_pdf_data,
            display_name="test.pdf"
        )
    )
    
    image_part = types.Part(
        inline_data=types.Blob(
            mime_type="image/jpeg",
            data=test_image_data,
            display_name="test.jpg"
        )
    )
    
    # Test PDF handling (will try Files API, fall back to base64)
    try:
        pdf_result = await openai_with_files._handle_file_data(pdf_part)
        print(f"PDF handling result: {pdf_result['type']}")
    except Exception as e:
        print(f"PDF handling error: {e}")
    
    # Test image handling (always base64)
    try:
        image_result = await openai_with_files._handle_file_data(image_part)
        print(f"Image handling result: {image_result['type']}")
    except Exception as e:
        print(f"Image handling error: {e}")
    
    # Test with Files API disabled
    print("\n2. Testing with Files API disabled...")
    openai_no_files = OpenAI(model="gpt-4o", use_files_api=False)
    
    try:
        pdf_result = await openai_no_files._handle_file_data(pdf_part)
        print(f"PDF handling result: {pdf_result['type']}")
    except Exception as e:
        print(f"PDF handling error: {e}")
    
    try:
        image_result = await openai_no_files._handle_file_data(image_part)
        print(f"Image handling result: {image_result['type']}")
    except Exception as e:
        print(f"Image handling error: {e}")


async def main():
    """Main example function."""
    await example_files_api_usage()
    await example_file_handling_comparison()
    
    print("\n" + "=" * 50)
    print("SUCCESS: OpenAI Files API examples completed!")
    print("\nKey Benefits of Files API Integration:")
    print("  - Better document processing for PDFs and Word docs")
    print("  - Automatic fallback to base64 if Files API fails")
    print("  - Configurable file handling strategy")
    print("  - Seamless integration with ADK agents")
    print("\nThe OpenAI integration now provides enterprise-grade file handling!")


if __name__ == "__main__":
    asyncio.run(main())
