# A2A Upload Middleware

This middleware provides A2A protocol support for file uploads, integrating with the ArtifactServiceWrapper for persistent storage.

## Features

- **Chunked Upload Support**: Handles large files by uploading them in chunks
- **Integrity Verification**: SHA256 checksum validation for uploaded files
- **Namespace Support**: Session-scoped and user-scoped artifact storage
- **Error Handling**: Comprehensive error handling with proper JSON-RPC error codes
- **Memory Management**: Automatic cleanup of old uploads to prevent memory leaks

## Usage

```python
from a2aExtensions.A2AUploadMiddleware import A2AUploadMiddleware
from modules.artifact_service import create_artifact_service

# Create middleware with default artifact service
app.add_middleware(A2AUploadMiddleware)

# Or with custom artifact service
artifact_service = create_artifact_service()
app.add_middleware(A2AUploadMiddleware, artifact_service=artifact_service)
```

## A2A Protocol Methods

The middleware supports the following JSON-RPC methods:

### artifactUpload/start
Start a new file upload session.

**Parameters:**
- `filename` (string): Name of the file to upload
- `mimeType` (string, optional): MIME type of the file (default: "application/octet-stream")
- `sha256` (string, optional): Expected SHA256 hash for integrity verification
- `userId` (string, optional): User ID for user-scoped artifacts
- `sessionId` (string, optional): Session ID for session-scoped artifacts

**Response:**
- `uploadId` (string): Unique identifier for this upload session
- `maxChunkBytes` (number): Maximum chunk size (524288 bytes)

### artifactUpload/append
Append data to an ongoing upload.

**Parameters:**
- `uploadId` (string): Upload session identifier
- `chunkBase64` (string): Base64-encoded chunk data
- `offset` (number, optional): Expected offset (default: 0)

**Response:**
- `received` (number): Number of bytes received in this chunk
- `total` (number): Total bytes received so far

### artifactUpload/finish
Complete the upload and save the artifact.

**Parameters:**
- `uploadId` (string): Upload session identifier
- `scope` (string, optional): "session" or "user" (default: "session")

**Response:**
- `filename` (string): Final filename
- `mimeType` (string): MIME type of the file
- `size` (number): Total file size in bytes
- `namespace` (string): Namespace where the artifact was saved

### artifactUpload/abort
Cancel an ongoing upload.

**Parameters:**
- `uploadId` (string): Upload session identifier

**Response:**
- `aborted` (boolean): Always true

## Namespace Handling

- **Session-scoped artifacts**: Stored with namespace `session:{sessionId}`
- **User-scoped artifacts**: Stored with namespace `user`

## Error Codes

- `-32004`: Invalid upload ID
- `-32005`: Incorrect offset
- `-32006`: SHA256 mismatch
- `-32007`: Failed to save artifact
- `-32602`: Invalid parameters
- `-32603`: Internal error
- `-32700`: Parse error

## Memory Management

The middleware includes automatic cleanup of old uploads to prevent memory leaks. Use the `cleanup_old_uploads()` method to manually trigger cleanup:

```python
middleware = A2AUploadMiddleware(app)
middleware.cleanup_old_uploads(max_age_seconds=3600)  # Clean up uploads older than 1 hour
```
