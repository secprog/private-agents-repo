"""
Orchestrator Agent - Main entry point using ADK SDK
"""

import logging
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from modules.orchestrator_core import OrchestratorCore
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard
from a2aExtensions.A2AUploadMiddleware import A2AUploadMiddleware

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize orchestrator
orchestrator_core = OrchestratorCore()

# Create A2A server using ADK SDK directly
root_agent = orchestrator_core.workflow_agent
agent_card = AgentCard(
    name=orchestrator_core.agent_id,
    url="http://0.0.0.0:8000",
    description=orchestrator_core.workflow_agent.description,
    version="1.0.0",
    capabilities={
        "extensions": [
            {
                "uri": "urn:orquestrator:artifact-upload:v1",
                "description": "File Upload chunked (start/append/finish).",
                "required": False,
                "params": {"maxChunkBytes": 1000000}, #1MB
            }
        ]
    },
    skills=[],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)
app = to_a2a(root_agent, port=8000, agent_card=agent_card)


# Add A2A Upload middleware
app.add_middleware(A2AUploadMiddleware)

# Add CORS middleware to A2A app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-A2A-Extensions"],  # Explicitly allow A2A extension header
)

# Add custom endpoints to the A2A app
@app.route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "healthy", "agent_id": orchestrator_core.agent_id})

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
