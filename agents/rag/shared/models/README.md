# OpenAI Integration for Google ADK

This module provides a native OpenAI integration for the Google Agent Development Kit (ADK), allowing you to use OpenAI GPT models without relying on LiteLLM.

## Features

- ✅ Native OpenAI API integration
- ✅ Support for all OpenAI models (GPT-4, GPT-3.5, O1, etc.)
- ✅ Function/tool calling support
- ✅ Streaming and non-streaming responses
- ✅ Image input support (base64 encoded)
- ✅ PDF and document support (for vision models)
- ✅ Usage metadata tracking
- ✅ Seamless integration with ADK's Agent

## Installation

1. Install the required dependencies:
```bash
pip install openai>=1.40.0
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

## Usage

### Basic Usage

```python
from shared.models import OpenAI
from google.adk.agents import Agent

# Method 1: Using model string (recommended)
agent = Agent(
    name="my_agent",
    description="An agent powered by OpenAI",
    model="gpt-4o"  # Automatically uses our OpenAI implementation
)

# Method 2: Using OpenAI instance
openai_llm = OpenAI(model="gpt-4o", max_tokens=500, temperature=0.7)
agent = Agent(
    name="my_agent",
    description="An agent with custom OpenAI config",
    model=openai_llm
)
```

### Supported Models

The integration supports all OpenAI models:

- **GPT-4 Models**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- **GPT-3.5 Models**: `gpt-3.5-turbo`
- **O1 Models**: `o1-preview`, `o1-mini`
- **Other Models**: `dall-e-*`, `tts-*`, `whisper-*`

### Custom Configuration

```python
from shared.models import OpenAI

# Create OpenAI instance with custom settings
openai_llm = OpenAI(
    model="gpt-4o",
    api_key="your-custom-key",  # Optional, defaults to OPENAI_API_KEY env var
    base_url="https://api.openai.com/v1",  # Optional, for custom endpoints
    max_tokens=1000,
    temperature=0.8
)

agent = Agent(
    name="custom_agent",
    model=openai_llm
)
```

### Function Calling

The integration automatically handles function calling:

```python
from google.adk.tools import BaseTool

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool")
    
    def _get_declaration(self):
        return types.FunctionDeclaration(
            name="my_tool",
            description="A sample tool",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "input": types.Schema(
                        type=types.Type.STRING,
                        description="Input parameter"
                    )
                },
                required=["input"]
            )
        )

# Add tools to your agent
agent = Agent(
    name="tool_agent",
    model="gpt-4o"
)
agent.add_tool(MyTool())
```

### File Handling

OpenAI supports various file types through their Chat Completions API and Files API:

**Supported File Types:**
- **Images**: PNG, JPEG, GIF, WebP (base64 encoded)
- **PDFs**: Via Files API upload or base64 for vision models (GPT-4o, GPT-4o-mini, o1)
- **Documents**: Word documents, etc. (via Files API or base64 for vision models)

**File Handling Methods:**
1. **Files API Upload**: Documents are uploaded to OpenAI's Files API for better processing
2. **Base64 Encoding**: Images and fallback for documents (for vision models)
3. **File References**: Converted to text descriptions (not supported by OpenAI Chat API)

**File Size Limits:**
- Maximum 100 pages per PDF
- Maximum 32MB total content per request
- Requires vision-capable models for document processing

**Example with Files:**
```python
from google.genai import types

# Create content with image
content = types.Content(
    role="user",
    parts=[
        types.Part(text="What's in this image?"),
        types.Part(inline_data=types.Blob(
            mime_type="image/jpeg",
            data=image_bytes
        ))
    ]
)

# Create content with PDF (will be uploaded to Files API)
pdf_content = types.Content(
    role="user",
    parts=[
        types.Part(text="Analyze this document:"),
        types.Part(inline_data=types.Blob(
            mime_type="application/pdf",
            data=pdf_bytes,
            display_name="document.pdf"
        ))
    ]
)

# The integration automatically handles file uploads
agent = Agent(model="gpt-4o")  # Vision-capable model required
```

**Configuration Options:**
```python
# Enable Files API (default)
openai_llm = OpenAI(
    model="gpt-4o",
    use_files_api=True  # Upload documents to Files API
)

# Disable Files API (use base64 only)
openai_llm = OpenAI(
    model="gpt-4o",
    use_files_api=False  # Use base64 encoding for all files
)
```

**Note**: File references (URIs) are not supported by OpenAI's Chat API. Files must be provided as base64-encoded inline data or uploaded via the Files API.

## Integration with Existing Agents

To use OpenAI in your existing agents, simply import the shared models:

```python
# In your agent file (e.g., agents/cybersecurity/cybersecurity_agent.py)
from shared.models import OpenAI  # This auto-registers the models

# Then use OpenAI models in your agent
self.agent = Agent(
    name=valid_name,
    description="Your agent description",
    model="gpt-4o"  # Now uses OpenAI instead of Gemini
)
```

## Testing

Run the test script to verify the integration:

```bash
python test_openai_integration.py
```

## Examples

See `examples/openai_agent_example.py` for complete usage examples.

## Architecture

The implementation follows the ADK's modular architecture:

1. **OpenAI Class**: Inherits from `BaseLlm` and implements `generate_content_async()`
2. **Content Conversion**: Converts between ADK's `types.Content` and OpenAI's message format
3. **Tool Conversion**: Converts ADK's function declarations to OpenAI's tool format
4. **Registry Integration**: Automatically registers with ADK's `LLMRegistry`

## Error Handling

The integration includes comprehensive error handling:

- API key validation
- Network error handling
- Response parsing errors
- Tool calling errors

## Performance

- Direct OpenAI API calls (no LiteLLM overhead)
- Efficient content conversion
- Streaming support for real-time responses
- Proper async/await patterns

## Migration from LiteLLM

If you're currently using LiteLLM for OpenAI models, you can easily migrate:

```python
# Before (LiteLLM)
from google.adk.models.lite_llm import LiteLLM
agent = Agent(model=LiteLLM(model="gpt-4o"))

# After (Native OpenAI)
from shared.models import OpenAI
agent = Agent(model="gpt-4o")  # Automatically uses our OpenAI implementation
```

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```
   Error: OPENAI_API_KEY environment variable not set
   ```
   Solution: Set your OpenAI API key as an environment variable.

2. **Model Not Found**
   ```
   Error: Model gpt-4o not found
   ```
   Solution: Ensure you've imported `shared.models` to register the models.

3. **Import Errors**
   ```
   Error: No module named 'shared.models'
   ```
   Solution: Add the project root to your Python path or install the package.

### Debug Mode

Enable debug logging to see detailed request/response information:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Contributing

To add support for additional OpenAI features:

1. Extend the `OpenAI` class in `openai_llm.py`
2. Add conversion functions for new content types
3. Update the `supported_models()` method if needed
4. Add tests in `test_openai_integration.py`
