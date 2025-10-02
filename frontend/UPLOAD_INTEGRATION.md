# A2A Upload Integration

This document explains how the frontend integrates with the A2A upload extension for file handling.

## Overview

The frontend now uses the A2A upload extension to handle file uploads instead of embedding files directly in messages. This provides better performance, larger file support, and proper artifact management.

## Flow

### 1. File Selection
- User clicks the attach button and selects files
- Files are validated (max 50MB per file)
- A new session is created if none exists

### 2. Upload Process
- Files are uploaded using the A2A upload extension
- Upload happens in 1MB chunks for better reliability
- Progress is shown in real-time
- Files are stored in the artifact service with proper namespacing

### 3. Message Sending
- When sending a message, uploaded files are referenced by filename and namespace
- No file data is embedded in the message payload
- The A2A protocol handles file retrieval on the backend

## Key Components

### A2AUploadService
- Handles all upload operations
- Manages chunked uploads
- Provides progress callbacks
- Handles error scenarios

### File Attachment Flow
1. `handleFileAttachment()` - Initiates upload process
2. `uploadService.uploadFile()` - Performs chunked upload
3. `updateUploadProgress()` - Updates UI with progress
4. `updateAttachmentsPreview()` - Shows upload status

### Message Integration
- `sendMessage()` - References uploaded files instead of embedding data
- Files are included as `file` parts with `filename` and `namespace`
- Backend can retrieve files using the artifact service

## Benefits

1. **Performance**: No large file data in message payloads
2. **Reliability**: Chunked uploads with progress tracking
3. **Scalability**: Files stored in artifact service, not in memory
4. **User Experience**: Real-time upload progress and status
5. **Error Handling**: Proper error messages and recovery

## File Size Limits

- **Frontend**: 50MB per file (configurable)
- **Backend**: Limited by artifact service configuration
- **Chunk Size**: 1MB (optimized for network conditions) - max value supported by ADK and A2A

## Error Handling

- Network errors during upload
- File size validation
- Upload progress tracking
- Graceful fallback for failed uploads

## Future Enhancements

- Resume interrupted uploads
- Parallel file uploads
- Upload cancellation
- File preview before upload
- Drag and drop support
