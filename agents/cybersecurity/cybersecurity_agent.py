"""
Cybersecurity Agent - Main entry point using ADK SDK
"""
import os
import logging
from google.adk.artifacts import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.apps.app import App, ResumabilityConfig
import uvicorn
from google.adk.planners.built_in_planner import BuiltInPlanner
from fastapi.middleware.cors import CORSMiddleware
from google.adk.models import LiteLlm
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.genai import types
from modules.architecture_analysis import ArchitectureAnalysis
# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_name = "cybersecurity-agent"
app_identifier = agent_name.replace("-", "_")

# Thinking configuration for extended reasoning
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "1024"))
INCLUDE_THOUGHTS = os.getenv("INCLUDE_THOUGHTS", "true").lower() == "true"

# Create thinking config for planners
thinking_config = types.ThinkingConfig(
    include_thoughts=INCLUDE_THOUGHTS,
    thinking_budget=THINKING_BUDGET
)

# Initialize services
# Use postgresql+psycopg:// for async driver (psycopg 3.x)
db_url = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/agent_platform")
# Convert postgresql:// to postgresql+psycopg:// for async support
if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
session_service = DatabaseSessionService(db_url=db_url)

# Initialize security analyzer (no longer needs artifact service - receives JSON from vision agent)
architecture_analysis = ArchitectureAnalysis()

# Create security analysis sub-agent
# This agent receives comprehensive visual analysis from the vision agent
# and performs security-focused analysis
security_analyzer_sub_agent = Agent(
    name="security_analyzer",
    description="Specialized sub-agent for security analysis of architecture diagrams using comprehensive vision data",
    model=LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5.1")),
    instruction="""You are a cybersecurity architecture specialist.

You receive comprehensive visual analysis data from the vision agent including:
- Visual components, connections, and zones
- Trust boundaries and security zones
- Detected technologies and frameworks
- Inferred relationships and dependencies
- Annotations and legend mappings

Your task is to perform thorough security analysis:
1. Identify security threats and vulnerabilities
2. Analyze potential attack paths
3. Check compliance with security frameworks
4. Provide actionable security recommendations

CRITICAL: 
- You MUST call the analyze_architecture_security tool with ALL available vision data
- Do not modify the input data
- Output the complete security analysis in JSON format
- Prioritize findings by risk level""",
    tools=[architecture_analysis.analyze_architecture_security],
    planner=BuiltInPlanner(thinking_config=thinking_config)
)


# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=app_identifier,
    description="Specialized agent for cybersecurity architecture analysis and threat assessment.",
    model=LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5.1")),
    instruction="""You are a cybersecurity specialist agent.
    
Your role is to analyze architecture diagrams for security threats, vulnerabilities, and compliance.

IMPORTANT WORKFLOW:
1. You receive comprehensive visual analysis data from the vision agent
2. You delegate security analysis to the security_analyzer sub-agent
3. The sub-agent returns detailed security findings and recommendations

You do NOT perform visual analysis yourself. You receive structured JSON data from the vision agent and focus on security assessment.

Delegate all security analysis tasks to the security_analyzer sub-agent.
Do not modify the input or output data.""",
    sub_agents=[security_analyzer_sub_agent],
    planner=BuiltInPlanner(thinking_config=thinking_config)
)

cyber_app = App(
    name=app_identifier,
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)


app = to_a2a(
    agent=root_agent,
    port=8001,
    host=agent_name,
    protocol="http",
    runner=Runner(
        app=cyber_app,
        artifact_service=InMemoryArtifactService(),
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
