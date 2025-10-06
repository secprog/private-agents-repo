"""
Cybersecurity Agent - Main entry point using ADK SDK
"""

import logging
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from google.adk.agents import Agent
from modules.architecture_analysis import architecture_sub_agent
from modules.custom_a2a import create_a2a_server_with_shared_session

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_name = "cybersecurity-agent"
# Initialize cybersecurity agent

# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=agent_name.replace("-", "_"),
    description="Specialized agent for cybersecurity.",
    model="gemini-2.0-flash",
    instruction="For cybersecurity tasks, you delegate to the most appropriate sub-agent.",
    sub_agents=[architecture_sub_agent]
)

app = create_a2a_server_with_shared_session(root_agent, port=8001, host=agent_name, protocol="http")

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