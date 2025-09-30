@echo off
echo 🚀 Activating shared virtual environment...
call "venv\Scripts\activate.bat"
echo ✅ Virtual environment activated!
echo.
echo 📋 Available commands:
echo   python -m agents.orchestrator.orchestrator    - Start orchestrator
echo   python -m agents.cybersecurity.cybersecurity_agent  - Start cybersecurity agent
echo   python -m agents.devops.devops_agent         - Start devops agent
echo   deactivate                                   - Deactivate virtual environment
echo.
