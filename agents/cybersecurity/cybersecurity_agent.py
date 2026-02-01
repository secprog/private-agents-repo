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

# Create security analysis sub-agent with multi-phase analysis tools
security_analyzer_sub_agent = Agent(
    name="security_analyzer",
    description="Specialized sub-agent for multi-phase security analysis of architecture diagrams",
    model=LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5.1")),
    instruction="""You are a cybersecurity architecture specialist performing multi-phase security analysis.

You receive GENERIC VISUAL DATA from the vision agent (component_type is a visual category like icon/labeled_box/shape - NOT IT roles). You must interpret it for security meaning.

WORKFLOW - Execute these steps IN ORDER:

1. **identify_security_context**: Call this FIRST with ALL visual data (components, connections, zones, boundaries, annotations, legend_mappings, line_crossings). This interprets generic visual facts into IT roles, technologies, protocols, encryption status, and security zones. Save the result as security_context_json.

2. **analyze_threats_and_vulnerabilities**: Call with security_context_json + original components_json, connections_json, boundaries_json. Identifies threats (STRIDE) and vulnerabilities. Save the result as threats_json.

3. **analyze_attack_paths**: Call with security_context_json + threats_json. Traces attack paths through the architecture. Save the result as attack_paths_json.

4. **assess_compliance**: Call with security_context_json. Checks compliance against GDPR, HIPAA, PCI DSS, SOC2, ISO 27001, NIST, CIS, OWASP. Save the result as compliance_json.

5. **generate_recommendations**: Call with security_context_json + threats_json + attack_paths_json + compliance_json. Produces prioritized recommendations, security posture score, and executive summary.

CRITICAL:
- Execute ALL 5 steps in sequence - each builds on previous results
- Pass the JSON output from each step as input to the next
- Do not skip any step
- Return the COMPLETE results from all steps""",
    tools=[
        architecture_analysis.identify_security_context,
        architecture_analysis.analyze_threats_and_vulnerabilities,
        architecture_analysis.analyze_attack_paths,
        architecture_analysis.assess_compliance,
        architecture_analysis.generate_recommendations,
    ],
    planner=BuiltInPlanner(thinking_config=thinking_config)
)


# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=app_identifier,
    description="Specialized agent for cybersecurity architecture analysis and threat assessment.",
    model=LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5.1")),
    instruction="""You are a cybersecurity specialist agent.

Your role is to analyze architecture diagrams for security threats, vulnerabilities, and compliance.

WORKFLOW:
1. You receive generic visual analysis data from the vision agent (JSON)
2. You delegate to the security_analyzer sub-agent which performs multi-phase analysis:
   - Phase 1: Interpret visual data into security context (technologies, protocols, zones)
   - Phase 2: Identify threats and vulnerabilities
   - Phase 3: Analyze attack paths
   - Phase 4: Assess compliance
   - Phase 5: Generate recommendations and security posture score
3. Return the complete analysis results

You do NOT perform visual analysis yourself. Pass ALL received visual data to the security_analyzer sub-agent.
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
