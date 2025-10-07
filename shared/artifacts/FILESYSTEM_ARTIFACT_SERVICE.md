# Filesystem Artifact Service

A local filesystem-based implementation of the ADK Artifact Service that stores artifacts on disk instead of in memory or cloud storage.

## Features

- **Persistent Storage**: Artifacts are saved to the local filesystem and persist between restarts
- **Same API**: Compatible with ADK's `BaseArtifactService` interface
- **Namespace Support**: Supports both session-scoped and user-scoped artifacts
- **Version Management**: Multiple versions of the same artifact are supported
- **Metadata Storage**: MIME types and content types are preserved
- **Async Operations**: All operations are async-compatible using `asyncio.to_thread`

## Directory Structure

The service creates a directory structure that mirrors the ADK artifact naming convention:

```
artifacts/                          # Base path (configurable)
├── agent-platform/                 # App name
│   └── default-user/               # User ID
│       ├── session-123/            # Session-scoped artifacts
│       │   └── document.pdf/       # Artifact filename
│       │       ├── 0               # Version 0 (binary data)
│       │       ├── 0.meta          # Version 0 metadata (MIME type)
│       │       ├── 1               # Version 1 (binary data)
│       │       └── 1.meta          # Version 1 metadata
│       └── user/                   # User-scoped artifacts
│           └── user:profile.png/   # User-scoped artifact
│               ├── 0               # Version 0
│               └── 0.meta          # Version 0 metadata
```

## Configuration

### Environment Variables

- `ARTIFACT_SERVICE_TYPE=filesystem` - Enable filesystem service
- `FILESYSTEM_ARTIFACT_PATH=./artifacts` - Base directory path (optional, defaults to `./artifacts`)

### Usage

```python
from modules.artifact_service import create_artifact_service

# Using environment variables
service = create_artifact_service()

# Or create directly
from modules.filesystem_artifact_service import FilesystemArtifactService
service = FilesystemArtifactService(base_path="./my-artifacts")
```

## File Storage

### Binary Files
- **Data**: Stored as-is in version files (e.g., `0`, `1`, `2`)
- **Metadata**: MIME type stored in `.meta` files (e.g., `0.meta`, `1.meta`)

### Text Files
- **Data**: Stored as UTF-8 text in version files
- **Metadata**: MIME type set to `text/plain` in `.meta` files

## Advantages

1. **Persistence**: Data survives application restarts
2. **Inspection**: Files can be directly accessed and inspected
3. **Backup**: Easy to backup with standard filesystem tools
4. **No Dependencies**: No external services required (unlike GCS)
5. **Performance**: Fast local disk access
6. **Development**: Great for development and testing

## Considerations

1. **Disk Space**: Artifacts consume local disk space
2. **Concurrency**: File locking handled by the OS
3. **Cleanup**: Old versions accumulate (manual cleanup may be needed)
4. **Portability**: Tied to the local filesystem

## Example Usage

```python
import asyncio
from modules.filesystem_artifact_service import FilesystemArtifactService
from google.genai.types import Part, Blob

async def example():
    service = FilesystemArtifactService(base_path="./test-artifacts")
    
    # Save an artifact
    artifact = Part(
        inline_data=Blob(
            mime_type="text/plain",
            data=b"Hello, World!"
        )
    )
    
    version = await service.save_artifact(
        app_name="my-app",
        user_id="user123",
        session_id="session456",
        filename="greeting.txt",
        artifact=artifact
    )
    
    # Load the artifact
    loaded = await service.load_artifact(
        app_name="my-app",
        user_id="user123", 
        session_id="session456",
        filename="greeting.txt",
        version=version
    )
    
    print(f"Loaded: {loaded.inline_data.data.decode()}")

# Run example
asyncio.run(example())
```

## Migration

To switch from in-memory to filesystem storage:

1. Set environment variable: `ARTIFACT_SERVICE_TYPE=filesystem`
2. Optionally set: `FILESYSTEM_ARTIFACT_PATH=/path/to/artifacts`
3. Restart the application

Existing in-memory artifacts will be lost, but new uploads will be persisted to disk.
