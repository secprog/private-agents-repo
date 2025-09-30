#!/bin/bash

echo "🚀 Setting up shared virtual environment for agent platform..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.11+ and try again"
    exit 1
fi

# Make setup script executable
chmod +x setup_simple_venv.py

# Run the setup script
python3 setup_simple_venv.py

if [ $? -eq 0 ]; then
    echo
    echo "✅ Setup completed successfully!"
    echo
    echo "📋 Next steps:"
    echo "  1. Activate virtual environment: source activate.sh"
    echo "  2. Start services with: docker-compose up"
    echo
else
    echo
    echo "❌ Setup failed! Please check the error messages above."
    echo
    exit 1
fi
