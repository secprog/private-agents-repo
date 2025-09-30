#!/usr/bin/env python3
"""
Simple setup script for single shared virtual environment
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up single shared virtual environment for agent platform...")
    
    # Get project root
    project_root = Path(__file__).parent
    venv_path = project_root / "venv"
    
    # Remove existing venv if it exists
    if venv_path.exists():
        print("🧹 Removing existing virtual environment...")
        if platform.system() == "Windows":
            run_command(f'rmdir /s /q "{venv_path}"', "Remove existing venv")
        else:
            run_command(f'rm -rf "{venv_path}"', "Remove existing venv")
    
    # Create new virtual environment
    if not run_command(f'python -m venv "{venv_path}"', "Create virtual environment"):
        return False
    
    # Determine activation script path
    if platform.system() == "Windows":
        activate_script = venv_path / "Scripts" / "activate.bat"
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        activate_script = venv_path / "bin" / "activate"
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Upgrade pip (skip on Windows to avoid permission issues)
    if platform.system() != "Windows":
        if not run_command(f'"{pip_path}" install --upgrade pip', "Upgrade pip"):
            return False
    else:
        print("⏭️ Skipping pip upgrade on Windows to avoid permission issues")
    
    # Install shared module first (editable install)
    shared_module_path = project_root / "agents" / "shared"
    if shared_module_path.exists():
        if not run_command(f'"{pip_path}" install -e "{shared_module_path}"', "Install shared module"):
            return False
    
    # Install shared requirements (without the -e ../shared line)
    shared_requirements = project_root / "agents" / "shared" / "requirements.txt"
    if shared_requirements.exists():
        if not run_command(f'"{pip_path}" install -r "{shared_requirements}"', "Install shared requirements"):
            return False
    
    # Install orchestrator requirements (without the -e ../shared line)
    orchestrator_requirements = project_root / "agents" / "orchestrator" / "requirements.txt"
    if orchestrator_requirements.exists():
        if not run_command(f'"{pip_path}" install -r "{orchestrator_requirements}"', "Install orchestrator requirements"):
            return False
    
    # Install cybersecurity requirements (without the -e ../shared line)
    cybersecurity_requirements = project_root / "agents" / "cybersecurity" / "requirements.txt"
    if cybersecurity_requirements.exists():
        if not run_command(f'"{pip_path}" install -r "{cybersecurity_requirements}"', "Install cybersecurity requirements"):
            return False
    
    # Install devops requirements (without the -e ../shared line)
    devops_requirements = project_root / "agents" / "devops" / "requirements.txt"
    if devops_requirements.exists():
        if not run_command(f'"{pip_path}" install -r "{devops_requirements}"', "Install devops requirements"):
            return False
    
    # Create activation script
    if platform.system() == "Windows":
        activation_script_content = f'''@echo off
echo 🚀 Activating shared virtual environment...
call "{activate_script}"
echo ✅ Virtual environment activated!
echo.
echo 📋 Available commands:
echo   python -m agents.orchestrator.orchestrator    - Start orchestrator
echo   python -m agents.cybersecurity.cybersecurity_agent  - Start cybersecurity agent
echo   python -m agents.devops.devops_agent         - Start devops agent
echo   deactivate                                   - Deactivate virtual environment
echo.
'''
        activation_script_path = project_root / "activate.bat"
    else:
        activation_script_content = f'''#!/bin/bash
echo "🚀 Activating shared virtual environment..."
source "{activate_script}"
echo "✅ Virtual environment activated!"
echo ""
echo "📋 Available commands:"
echo "  python -m agents.orchestrator.orchestrator    - Start orchestrator"
echo "  python -m agents.cybersecurity.cybersecurity_agent  - Start cybersecurity agent"
echo "  python -m agents.devops.devops_agent         - Start devops agent"
echo "  deactivate                                   - Deactivate virtual environment"
echo ""
'''
        activation_script_path = project_root / "activate.sh"
    
    with open(activation_script_path, 'w') as f:
        f.write(activation_script_content)
    
    if platform.system() != "Windows":
        os.chmod(activation_script_path, 0o755)
    
    print("\n🎉 Setup completed successfully!")
    print(f"📁 Virtual environment created at: {venv_path}")
    print(f"🔧 Activation script created: {activation_script_path}")
    print("\n📋 Next steps:")
    if platform.system() == "Windows":
        print("  1. Run: activate.bat")
        print("  2. Start services with: docker-compose up")
    else:
        print("  1. Run: source activate.sh")
        print("  2. Start services with: docker-compose up")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
