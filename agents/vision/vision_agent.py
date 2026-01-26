"""
Vision Agent - Main entry point using ADK SDK
"""

import os
import logging
import warnings
from google.adk.models import LiteLlm
from google.genai import types
from google.adk.planners.built_in_planner import BuiltInPlanner

# Suppress Pydantic serialization warnings from LiteLLM internal responses
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.apps.app import App, ResumabilityConfig
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from google.adk.tools.function_tool import FunctionTool
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.artifacts import FileArtifactService
from vision_analysis import VisionAnalysis
from prompts import get_merger_instructions

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_name = "vision-agent"
agent_identifier = agent_name.replace("-", "_")

# Thinking configuration for extended reasoning
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "1024"))
INCLUDE_THOUGHTS = os.getenv("INCLUDE_THOUGHTS", "true").lower() == "true"

# Create thinking config for planners
thinking_config = types.ThinkingConfig(
    include_thoughts=INCLUDE_THOUGHTS,
    thinking_budget=THINKING_BUDGET
)

# Initialize vision agent
artifact_service = FileArtifactService(
    root_dir=os.getenv("ARTIFACT_ROOT_DIR", "./my_artifacts")
)
# Use postgresql+psycopg:// for async driver (psycopg 3.x)
db_url = os.getenv(
    "DATABASE_URL", "postgresql://admin:admin123@localhost:5432/agent_platform"
)
# Convert postgresql:// to postgresql+psycopg:// for async support
if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
session_service = DatabaseSessionService(db_url=db_url)
vision_analysis = VisionAnalysis(artifact_service)

# Create vision analysis agent with multiple tools that can run in parallel
visual_analysis_agent = Agent(
    name="visual_analyzer",
    description="Specialized agent for analyzing visual elements from images with advanced capabilities",
    model=LiteLlm(model="openai/gpt-5.1"),
    instruction="""You are an advanced visual analysis agent specialized in extracting visual information from diagrams and images.

CORE PRINCIPLE: You are a VISUAL EXTRACTOR - you describe what you SEE, not what it means.
Extract colors, shapes, text, positions, visual markers objectively.
Downstream agents will interpret the visual facts you provide for their specific domains.

WORKFLOW:
1. run_core_analysis_parallel - Extract components, connections, zones (ALWAYS START HERE)
2. extract_boundaries - Extract visual boundaries and enclosures
3. extract_annotations - Extract text annotations, notes, callouts

ADDITIONAL TOOLS (use as needed):
- extract_text_from_image - Extract all text if core analysis missed text
- analyze_layout - Analyze layout structure and hierarchy
- analyze_styling - Analyze color patterns and visual conventions
- extract_legend_mappings - Extract legend symbols and meanings
- detect_line_crossings - Analyze line topology (advanced)
- identify_regions - Segment complex diagrams (advanced)
- compare_diagrams - Compare two diagrams (requires 2 files)

CRITICAL RULES:
1. Extract COMPLETE visual details: colors, shapes, text, icons, badges, markers, line styles
2. Do NOT interpret domain meaning (security, business, art, cooking, etc.)
3. Capture EVERY visual element - be thorough and specific
4. If no file is provided, ask for one - DO NOT call tools without a file

WORKFLOW EXAMPLE:
User: "Analyze this architecture diagram"
1. Call run_core_analysis_parallel → get components, connections, zones with ALL visual details
2. Call extract_boundaries → get visual boundaries
3. Call extract_annotations → get text annotations, notes, callouts
4. Return all extracted visual data

IMPORTANT:
- NEVER call tools without required parameters (user_id, session_id, filename)
- NEVER interpret what components mean or what the diagram represents
- ALWAYS extract visual facts objectively and completely
- Capture colors, visual badges, all text labels, line patterns, etc.
""",
    tools=[
        # Core extraction
        FunctionTool(func=vision_analysis.run_core_analysis_parallel),
        FunctionTool(func=vision_analysis.extract_boundaries),
        FunctionTool(func=vision_analysis.extract_annotations),
        # Text extraction
        FunctionTool(func=vision_analysis.extract_text_from_image),
        # Layout & structure
        FunctionTool(func=vision_analysis.analyze_layout),
        FunctionTool(func=vision_analysis.analyze_styling),
        # Advanced visual
        FunctionTool(func=vision_analysis.extract_legend_mappings),
        FunctionTool(func=vision_analysis.detect_line_crossings),
        FunctionTool(func=vision_analysis.identify_regions),
        # Comparison
        FunctionTool(func=vision_analysis.compare_diagrams),
    ],
    planner=BuiltInPlanner(thinking_config=thinking_config),
)

merger = Agent(
    name="merge_visual_analysis",
    description="Specialized sub-agent for merging visual analysis results into unified representation",
    model=LiteLlm(model="openai/gpt-5.1"),
    instruction=get_merger_instructions(),
)

# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=agent_identifier,
    description="Specialized agent for visual analysis of diagrams and images.",
    model=LiteLlm(model="openai/gpt-5.1"),
    instruction="""For visual analysis tasks, you have two sub-agents:
1. visual_analyzer - Performs visual extraction using tools to extract complete visual information
2. merge_visual_analysis - Merges visual analysis results into unified representation

KEY PRINCIPLES:
- You are a VISUAL EXTRACTION agent - extract visual facts, do NOT interpret meaning
- Extract colors, shapes, text, positions, icons, badges, line styles objectively
- Downstream agents will interpret the visual data for their domains

Workflow:
- For visual extraction: Delegate to visual_analyzer
- For merging results: Delegate to merge_visual_analysis
- You do not modify sub-agent input or output

IMPORTANT GUARDRAILS:
- If user asks general questions, respond directly
- ONLY delegate to sub-agents if a file/image is provided
- NEVER call tools when filename/session_id/user_id are missing
- If no file is present, ask user to provide one and stop""",
   sub_agents=[visual_analysis_agent, merger],
   planner=BuiltInPlanner(thinking_config=thinking_config),
)

vision_app = App(
    name=agent_identifier,
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

app = to_a2a(
    agent=root_agent,
    port=8002,
    host=agent_name,
    protocol="http",
    runner=Runner(
        app=vision_app,
        artifact_service=artifact_service,
        session_service=session_service,
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    ),
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
