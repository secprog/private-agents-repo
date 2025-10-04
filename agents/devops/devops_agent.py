"""
DevOps Agent - Main entry point using ADK SDK
"""

import logging
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from modules.devops_core import DevOpsCore
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from a2a.types import AgentCard

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize DevOps agent
devops_core = DevOpsCore()

# Create A2A server using ADK SDK directly
root_agent = devops_core.agent
agent_card = AgentCard(
    name=devops_core.agent_id,
    url="http://0.0.0.0:8002",
    description=devops_core.agent.description,
    version="1.0.0",
    capabilities={},
    skills=[],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)
app = to_a2a(root_agent, port=8002)

# Add CORS middleware to A2A app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No custom endpoints needed - ADK/A2A only uses .well-known/agent-card.json

# Add startup and shutdown handlers to A2A app
@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    await devops_core.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await devops_core.session_service.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)