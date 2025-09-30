"""
Orchestrator Agent - Main entry point using ADK SDK
"""

import logging
import uvicorn
from typing import Optional
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware

from modules.orchestrator_core import OrchestratorCore
from modules.api_handlers import APIHandlers
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize orchestrator and API handlers
orchestrator_core = OrchestratorCore()
api_handlers = APIHandlers(orchestrator_core)

# Create A2A server using ADK SDK directly
root_agent = orchestrator_core.workflow_agent
agent_card = AgentCard(
    name=orchestrator_core.agent_id,
    url="http://0.0.0.0:8000",
    description=orchestrator_core.workflow_agent.description,
    version="1.0.0",
    capabilities={},
    skills=[],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)
app = to_a2a(root_agent, port=8000, agent_card=agent_card)

# Add CORS middleware to A2A app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)  

# Add custom endpoints to the A2A app
@app.route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "agent_id": orchestrator_core.agent_id})


@app.route("/agents", methods=["GET"])
async def get_agents(request):
    """Get all discovered agents"""
    from starlette.responses import JSONResponse
    result = await api_handlers.get_agents()
    return JSONResponse(result)


@app.route("/tasks", methods=["GET"])
async def get_tasks(request):
    """Get tasks with optional status filter"""
    from starlette.responses import JSONResponse
    status = request.query_params.get("status")
    result = await api_handlers.get_tasks(status)
    return JSONResponse(result)


@app.route("/tasks/{task_id}", methods=["GET"])
async def get_task(request):
    """Get specific task by ID"""
    from starlette.responses import JSONResponse
    task_id = request.path_params["task_id"]
    result = await api_handlers.get_task(task_id)
    return JSONResponse(result)




# Add startup and shutdown handlers to A2A app
@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    await orchestrator_core.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await orchestrator_core.session_service.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)