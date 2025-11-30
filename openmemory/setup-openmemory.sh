#!/bin/bash
# Setup script for OpenMemory - automatically clones mem0 repository and copies API files
# Usage: ./setup-openmemory.sh

set -e

echo "========================================"
echo "OpenMemory Setup Script"
echo "========================================"
echo ""

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "ERROR: Git is not installed or not in PATH."
    echo "Please install Git: https://git-scm.com/"
    exit 1
fi

# Set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMP_CLONE="/tmp/mem0-clone"
OPENMEMORY_API="$SCRIPT_DIR/api"

echo "Step 1: Cloning mem0 repository..."
echo ""

# Remove existing temp clone if it exists
if [ -d "$TEMP_CLONE" ]; then
    echo "Removing existing temporary clone..."
    rm -rf "$TEMP_CLONE"
fi

# Clone the repository
if ! git clone https://github.com/mem0ai/mem0.git "$TEMP_CLONE"; then
    echo "ERROR: Failed to clone mem0 repository."
    exit 1
fi

echo ""
echo "Step 2: Copying API files..."
echo ""

# Check if api directory exists in the clone
if [ ! -d "$TEMP_CLONE/openmemory/api" ]; then
    echo "ERROR: openmemory/api directory not found in cloned repository."
    rm -rf "$TEMP_CLONE"
    exit 1
fi

# Create api directory if it doesn't exist
mkdir -p "$OPENMEMORY_API"

# Copy files
echo "Copying files from mem0/openmemory/api to openmemory/api..."
if ! cp -r "$TEMP_CLONE/openmemory/api"/* "$OPENMEMORY_API/"; then
    echo "ERROR: Failed to copy API files."
    rm -rf "$TEMP_CLONE"
    exit 1
fi

echo ""
echo "Step 3: Cleaning up temporary files..."
echo ""

# Remove the temporary clone
rm -rf "$TEMP_CLONE"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "OpenMemory API files have been copied to: $OPENMEMORY_API"
echo ""
echo "Next steps:"
echo "1. Set OPENAI_API_KEY in your .env file"
echo "2. Run: docker-compose up -d openmemory"
echo ""

