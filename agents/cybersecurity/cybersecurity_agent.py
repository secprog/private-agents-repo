"""
Cybersecurity Agent - Main entry point using ADK SDK
"""

import logging
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from modules.cybersecurity_core import CyberSecurityCore
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_name = "cybersecurity-agent"
# Initialize cybersecurity agent
cybersecurity_core = CyberSecurityCore(agent_name)

# Create A2A server using ADK SDK directly
root_agent = cybersecurity_core.agent

app = to_a2a(root_agent, port=8001, host=agent_name, protocol="http")

# Add CORS middleware to A2A app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app)