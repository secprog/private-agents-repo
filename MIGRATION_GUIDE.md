# Migration Guide: From Gemini to OpenAI

This guide shows how to migrate your existing ADK agents from Gemini to OpenAI models.

## Quick Migration

### Step 1: Import the OpenAI Integration

Add this import to your agent files:

```python
# Add this import at the top of your agent files
from shared.models import OpenAI
```

### Step 2: Update Agent Model Configuration

Change your agent model from Gemini to OpenAI:

```python
# Before (Gemini)
self.agent = Agent(
    name=valid_name,
    description="Your agent description",
    model="gemini-2.0-flash"
)

# After (OpenAI)
self.agent = Agent(
    name=valid_name,
    description="Your agent description",
    model="gpt-4o"  # or any other OpenAI model
)
```

## Detailed Migration Examples

### Cybersecurity Agent

**File**: `agents/cybersecurity/modules/cybersecurity_core.py`

```python
# Add import
from shared.models import OpenAI

class CyberSecurityCore:
    def __init__(self):
        # ... existing code ...
        
        # Change this line:
        self.agent = Agent(
            name=valid_name,
            description="Specialized agent for cybersecurity analysis, threat detection, and vulnerability assessment",
            model="gpt-4o"  # Changed from "gemini-2.0-flash"
        )
```

### DevOps Agent

**File**: `agents/devops/modules/devops_core.py`

```python
# Add import
from shared.models import OpenAI

class DevOpsCore:
    def __init__(self):
        # ... existing code ...
        
        # Change this line:
        self.agent = Agent(
            name=valid_name,
            description="Specialized agent for DevOps operations, deployment automation, and infrastructure management",
            model="gpt-4o"  # Changed from "gemini-2.0-flash"
        )
```

### Orchestrator Agent

**File**: `agents/orchestrator/modules/orchestrator_core.py`

```python
# Add import
from shared.models import OpenAI

class OrchestratorCore:
    def __init__(self):
        # ... existing code ...
        
        # Change this line:
        self.workflow_agent = Agent(
            name=valid_name,
            description="Master orchestrator for routing tasks to specialized agents",
            model="gpt-4o"  # Changed from "gemini-2.0-flash"
        )
```

## Environment Setup

### 1. Set OpenAI API Key

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-openai-api-key-here"

# Or add to your .env file
echo "OPENAI_API_KEY=your-openai-api-key-here" >> .env
```

### 2. Install Dependencies

The OpenAI package is already included in the requirements, but if you need to install it manually:

```bash
pip install openai>=1.40.0
```

## Model Selection

Choose the appropriate OpenAI model for your use case:

| Model | Best For | Cost | Speed | File Support |
|-------|----------|------|-------|--------------|
| `gpt-4o` | General purpose, high quality | High | Medium | Images, PDFs, Documents |
| `gpt-4o-mini` | Cost-effective, good quality | Low | Fast | Images, PDFs, Documents |
| `gpt-4-turbo` | Complex reasoning | High | Medium | Images only |
| `gpt-3.5-turbo` | Simple tasks, cost-effective | Low | Fast | Text only |
| `o1-preview` | Complex reasoning, code generation | Very High | Slow | Images, PDFs, Documents |
| `o1-mini` | Balanced reasoning | High | Medium | Images, PDFs, Documents |

**Note**: For file processing (PDFs, documents), use vision-capable models like `gpt-4o`, `gpt-4o-mini`, or `o1` models.

## File Handling Differences

### Gemini vs OpenAI File Support

| Feature | Gemini | OpenAI |
|---------|--------|--------|
| **Images** | ✅ Full support | ✅ Full support (vision models) |
| **PDFs** | ✅ Full support | ✅ Full support (Files API + vision models) |
| **Documents** | ✅ Full support | ✅ Full support (Files API + vision models) |
| **File References** | ✅ URI support | ❌ No URI support |
| **File Upload** | ✅ Direct upload | ✅ Files API + Base64 encoding |
| **File Size** | Large files supported | 32MB limit, 100 pages max |
| **Files API** | N/A | ✅ Native OpenAI Files API integration |

### Migration Considerations

1. **File References**: OpenAI doesn't support file URIs. Convert to base64 inline data:
   ```python
   # Before (Gemini)
   part = types.Part(file_data=types.FileData(
       file_uri="gs://bucket/file.pdf"
   ))
   
   # After (OpenAI)
   with open("file.pdf", "rb") as f:
       file_data = f.read()
   part = types.Part(inline_data=types.InlineData(
       mime_type="application/pdf",
       data=file_data
   ))
   ```

2. **Model Selection**: Use vision-capable models for file processing:
   ```python
   # For file processing, use vision models
   agent = Agent(model="gpt-4o")  # ✅ Supports files
   # agent = Agent(model="gpt-3.5-turbo")  # ❌ Text only
   ```

3. **File Size Limits**: OpenAI has stricter limits:
   - Maximum 32MB per request
   - Maximum 100 pages per PDF
   - Consider chunking large files

4. **Files API Configuration**: Choose between Files API upload or base64 encoding:
   ```python
   # Use Files API for documents (recommended)
   openai_llm = OpenAI(
       model="gpt-4o",
       use_files_api=True  # Upload PDFs/docs to Files API
   )
   
   # Use base64 encoding only (fallback)
   openai_llm = OpenAI(
       model="gpt-4o",
       use_files_api=False  # All files as base64
   )
   ```

## Advanced Configuration

### Custom OpenAI Settings

```python
from shared.models import OpenAI

# Create custom OpenAI instance
openai_llm = OpenAI(
    model="gpt-4o",
    max_tokens=1000,
    temperature=0.7,
    api_key="your-custom-key",  # Optional
    base_url="https://api.openai.com/v1"  # Optional
)

# Use in agent
agent = Agent(
    name="custom_agent",
    description="Agent with custom OpenAI settings",
    model=openai_llm
)
```

### Environment-Specific Configuration

```python
import os
from shared.models import OpenAI

# Use different models for different environments
if os.getenv("ENVIRONMENT") == "production":
    model = "gpt-4o"
elif os.getenv("ENVIRONMENT") == "staging":
    model = "gpt-4o-mini"
else:
    model = "gpt-3.5-turbo"

agent = Agent(
    name="env_aware_agent",
    description="Environment-aware agent",
    model=model
)
```

## Testing Your Migration

### 1. Run Registration Tests

```bash
python test_openai_registration.py
```

### 2. Test with API Key

```bash
# Set your API key
export OPENAI_API_KEY="your-key-here"

# Run full integration test
python test_openai_integration.py
```

### 3. Test Individual Agents

```bash
# Test cybersecurity agent
python examples/cybersecurity_agent_openai.py
```

## Troubleshooting

### Common Issues

1. **Import Error**: `ModuleNotFoundError: No module named 'shared.models'`
   - **Solution**: Ensure you're running from the project root and the Python path is correct

2. **Model Not Found**: `ValueError: Model gpt-4o not found`
   - **Solution**: Make sure you've imported `shared.models` to trigger registration

3. **API Key Error**: `OPENAI_API_KEY environment variable not set`
   - **Solution**: Set your OpenAI API key as an environment variable

4. **Permission Error**: `Permission denied` when accessing OpenAI API
   - **Solution**: Check your API key permissions and billing status

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

### Cost Optimization

- Use `gpt-4o-mini` for simple tasks
- Use `gpt-3.5-turbo` for high-volume, low-complexity tasks
- Set appropriate `max_tokens` limits
- Monitor usage through OpenAI dashboard

### Speed Optimization

- Use `gpt-4o-mini` for faster responses
- Implement caching for repeated requests
- Use streaming for real-time responses

## Rollback Plan

If you need to rollback to Gemini:

1. Remove the `from shared.models import OpenAI` import
2. Change model back to `"gemini-2.0-flash"`
3. Ensure Google ADK credentials are still configured

## Support

For issues with the OpenAI integration:

1. Check the logs for detailed error messages
2. Verify your API key and permissions
3. Test with the provided test scripts
4. Review the OpenAI API documentation

## Next Steps

After successful migration:

1. Monitor performance and costs
2. Optimize model selection based on use cases
3. Implement proper error handling
4. Set up monitoring and alerting
5. Consider implementing fallback mechanisms
