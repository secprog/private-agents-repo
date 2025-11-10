"""
Cybersecurity Agent - Main entry point using ADK SDK
"""
import os
import logging
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.artifacts import FileArtifactService
from modules.architecture_analysis import ArchitectureAnalyzer
# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_name = "cybersecurity-agent"
# Initialize cybersecurity agent
artifact_service = FileArtifactService(root_dir=os.getenv("ARTIFACT_ROOT_DIR", "./my_artifacts"))
session_service = DatabaseSessionService(db_url=os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/agent_platform"))

architecture_analyzer = ArchitectureAnalyzer(artifact_service=artifact_service)

# Create architecture analysis sub-agent
architecture_sub_agent = Agent(
    name="architecture_analyzer",
    description="Specialized sub-agent for analyzing system architecture diagrams",
    model="gemini-2.0-flash",
    instruction="Analyze architecture diagrams and extract components, connections, technologies, and security domains, outputs in json format",
    tools=[architecture_analyzer.analyze_architecture]
)

cybersecurity_architect_sub_agent = Agent(
    name="cybersecurity_architect",
    description="Specialized sub-agent for analyzing system architecture diagrams and provide cybersecurity recommendations and risk assessments",
    model="gemini-2.0-flash",
    instruction="Based on the json output of the architecture_analyzer sub-agent, provide cybersecurity recommendations and risk assessments outputs in json format",
    tools=[architecture_analyzer.security_analysis]
)

# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=agent_name.replace("-", "_"),
    description="Specialized agent for cybersecurity.",
    model="gemini-2.0-flash",
    instruction="For cybersecurity tasks, you delegate to the most appropriate sub-agent.",
    sub_agents=[architecture_sub_agent, cybersecurity_architect_sub_agent],
)

app = to_a2a(
    agent=root_agent,
    port=8001,
    host=agent_name,
    protocol="http",
    runner=Runner(
        app_name=agent_name,
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    )
)

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
