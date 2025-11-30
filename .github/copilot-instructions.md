<!-- Copilot instructions for contributors and AI assistants -->
# Agent Platform — Copilot Instructions

This file contains concise, actionable guidance for AI coding agents working in the `agent-platform` repository.

- Big picture:
  - **Purpose:** a multi-agent AI platform with a central `Orchestrator` that routes tasks to specialized agents (CyberSecurity, DevOps, Vision, RAG, etc.). Designed for secure A2A (agent-to-agent) communication and modular agent development.
  - **Where to look:** primary code lives under `agents/` (e.g. `agents/orchestrator`, `agents/cybersecurity`, `agents/devops`, `agents/vision`) and the frontend under `frontend/`.

- Architecture & boundaries:
  - `Orchestrator` (only externally exposed agent) receives A2A messages and routes tasks to internal agents via HTTPS A2A protocol. See `agents/orchestrator/orchestrator.py`.
  - Internal agents implement domain logic and are intended to be reachable only from the orchestrator (Docker internal network when using `docker-compose`). Examples: `agents/cybersecurity/cybersecurity_agent.py`, `agents/vision/vision_agent.py`.
  - Shared libraries / models are placed in `agents/shared/` (LLM wrappers, A2A client, models). Reuse these to avoid duplication.

- Developer workflows & common commands:
  - Quick start (Docker Compose): build and run everything:
    ```powershell
    docker-compose up -d
    docker-compose logs -f orchestrator
    ```
  - Local development (shared venv): repository includes `activate.bat`, `activate.sh`, and `setup_simple_venv.py` for a shared virtualenv. Typical flow:
    ```powershell
    # Windows (powershell)
    python setup_simple_venv.py
    .\venv\Scripts\Activate.ps1    # or run activate.bat
    cd agents/orchestrator
    pip install -r requirements.txt
    python -m agents.orchestrator.orchestrator
    ```
  - Frontend: `cd frontend && npm install && npm start` (serves on http://localhost:3000 by default).

- Project-specific conventions and patterns:
  - A2A message format: messages are JSON objects with `id`, `sender_id`, `recipient_id`, `message_type`, `content`, `metadata`, and `timestamp`. See examples in `README.md`.
  - Security model: only `orchestrator` is exposed externally; other agents are internal. Assume TLS in examples and docker-compose during development uses self-signed certs.
  - Shared virtualenv: repository intentionally uses a single `venv/` at repo root for all agents—avoid splitting environments unless necessary.
  - File uploads / attachments: frontend sends attachments embedded in A2A messages; agents should expect base64-encoded blobs or file references.

- Integration points & external dependencies:
  - LLM providers: environment-driven; support for OpenAI / Azure / Gemini via env vars (see top-level README). Typical env vars: `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_BASE_URL`, `AZURE_OPENAI_ENDPOINT`.
  - Docker Compose: `docker-compose.yml` orchestrates containers and internal networking — use it for integration testing.
  - SSL/TLS: development uses self-signed certs; production must use CA-signed certs. Uvicorn commands in README show `--ssl-keyfile` / `--ssl-certfile` for testing.

- Tests, debugging & common pitfalls:
  - Unit tests are primarily in each agent's folder or top-level `test_*.py` integration tests referenced from `README.md`. Use `pytest -q` when inside the venv.
  - If agents fail to discover each other, check Docker network and the orchestrator's registry endpoints; use `docker-compose logs` to inspect startup logs.
  - For LLM integration failures, verify the corresponding env var and API key, and check rate limits or credentials.

- Files to consult when making changes:
  - `agents/orchestrator/orchestrator.py` — A2A routing, agent registry, and HTTP endpoints.
  - `agents/*/*_agent.py` — Concrete agent implementations and FastAPI/Uvicorn servers.
  - `frontend/` — JS client showing how A2A messages are constructed and sent.
  - `docker-compose.yml` and `start.cmd` — Docker-based workflows and Windows entrypoints.

- PR guidance for reviewers:
  - Provide a short design note explaining where changes live (which agent, shared module), and how routing or A2A semantics are preserved.
  - Include environment variables required to run the change locally and any certificate instructions.
  - Add focused tests for message schema, agent discovery, and state serialization when changing core A2A behavior.

If you want me to expand any section (example A2A messages, cert instructions, or a short contributor checklist), say which part and I will add more detail.
 
-- Examples & Quick Snippets:
- A2A message example (common shape used across projects):
  ```json
  {
    "id": "msg_123",
    "sender_id": "agent_or_frontend",
    "recipient_id": "orchestrator",
    "message_type": "chat_request",
    "content": {
      "session_id": "session_789",
      "user_id": "user_456",
      "content": "Analyze this code for security vulnerabilities",
      "attachments": []
    },
    "metadata": { "timestamp": "2025-11-30T00:00:00Z", "source": "frontend" }
  }
  ```

- How to run tests locally (agent-platform):
  ```powershell
  # create + activate shared venv (repo root)
  python setup_simple_venv.py
  .\venv\Scripts\Activate.ps1

  # Run unit tests (inside venv)
  pytest -q

  # Integration tests (docker-compose based)
  docker-compose -f docker-compose.test.yml up --abort-on-container-exit
  ```

- CI / Local checklist (quick):
  - Required env vars for local testing: `OPENAI_API_KEY` or `AZURE_OPENAI_API_KEY`, `GOOGLE_API_KEY` (if using Gemini), `REDIS_URL` or local Redis running, `OPEN_MEMORY_API_KEY` (if testing OpenMemory integrations).
  - SSL certs: development uses self-signed certs; place `key.pem` / `cert.pem` in repository root or point Uvicorn `--ssl-keyfile`/`--ssl-certfile` to your dev certs.
  - Use `docker-compose logs -f orchestrator` to inspect orchestrator startup and agent registration.

