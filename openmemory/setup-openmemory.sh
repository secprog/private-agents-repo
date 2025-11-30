#!/bin/bash
# Setup script for CaviraOSS OpenMemory - automatically clones repository and copies backend files
# Usage: ./setup-openmemory.sh
# See: https://github.com/CaviraOSS/OpenMemory

set -e

echo "========================================"
echo "CaviraOSS OpenMemory Setup Script"
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
TEMP_CLONE="/tmp/openmemory-cavira-clone"

echo "Step 1: Cloning CaviraOSS OpenMemory repository..."
echo ""

# Remove existing temp clone if it exists
if [ -d "$TEMP_CLONE" ]; then
    echo "Removing existing temporary clone..."
    rm -rf "$TEMP_CLONE"
fi

# Clone the repository
if ! git clone https://github.com/CaviraOSS/OpenMemory.git "$TEMP_CLONE"; then
    echo "ERROR: Failed to clone CaviraOSS OpenMemory repository."
    exit 1
fi

echo ""
echo "Step 2: Copying backend files..."
echo ""

# Check if backend directory exists in the clone
if [ ! -d "$TEMP_CLONE/backend" ]; then
    echo "ERROR: backend directory not found in cloned repository."
    rm -rf "$TEMP_CLONE"
    exit 1
fi

# Copy backend files directly to openmemory directory (not to a subfolder)
echo "Copying files from OpenMemory/backend to openmemory/..."
if ! cp -r "$TEMP_CLONE/backend"/* "$SCRIPT_DIR/"; then
    echo "ERROR: Failed to copy backend files."
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
echo "CaviraOSS OpenMemory backend files have been copied to: $SCRIPT_DIR"
echo ""
echo "Next steps:"
echo "1. Set required environment variables in your .env file (check CaviraOSS OpenMemory docs)"
echo "2. Run: docker-compose up -d openmemory"
echo ""
echo "For more information, see: https://github.com/CaviraOSS/OpenMemory"
echo ""
