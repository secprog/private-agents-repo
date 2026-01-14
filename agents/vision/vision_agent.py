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
    instruction="""You are an advanced visual analysis agent specialized in analyzing diagrams and images.

You have multiple tools available for comprehensive analysis:

CORE ANALYSIS (single parallel bundle):
1. run_core_analysis_parallel - Runs component, connection, and zone analysis at the same time and returns:
   * components / connections / zones arrays
   * components_json / connections_json / zones_json raw payloads

OCR & TEXT EXTRACTION (accurate text recognition):
2. extract_text_from_image - Extracts text using GPT
3. extract_text_with_paddleocr - Extracts text using PaddleOCR (more accurate)
4. extract_text_with_consensus - Uses both GPT and PaddleOCR for best results

ENHANCEMENT ANALYSIS (parallel bundle):
5. run_enhancement_analysis_parallel - Runs technology detection, diagram classification, and annotation extraction together and returns parsed + raw JSON
6. detect_technologies - Identifies technologies, cloud services, frameworks
7. classify_diagram_type - Classifies diagram type, notation, and style
8. extract_annotations - Extracts notes, callouts, warnings

ANALYSIS TOOLS (for deeper understanding):
9. analyze_layout - Analyzes layout structure and hierarchy
10. analyze_styling - Analyzes color coding and visual conventions
11. infer_relationships - Infers logical relationships not shown visually

QUALITY TOOLS (require analysis results as input):
12. validate_visual_analysis - Validates analysis quality (requires: components_json, connections_json, zones_json)
13. enhance_analysis - Enhances initial analysis (requires: initial_analysis_json)
14. assess_image_quality - Assesses image quality before analysis

ADVANCED ANALYSIS:
15. identify_regions - Identifies logical regions in complex diagrams

EXPORT TOOLS (require analysis results):
16. export_to_plantuml - Converts analysis to PlantUML code (requires: components_json, connections_json, zones_json)
17. export_to_mermaid - Converts analysis to Mermaid code (requires: components_json, connections_json, zones_json)
18. export_to_drawio - Converts analysis to draw.io XML (requires: components_json, connections_json, zones_json)

ADVANCED VISION TOOLS:
19. extract_legend_mappings - Extract and parse diagram legends
20. detect_line_crossings - Detect line crossings vs actual intersections (requires: connections_json)
21. detect_trust_boundaries - Identify security/trust boundaries (optional: components_json)

COMPARISON TOOLS:
22. compare_diagrams - Compares two diagrams (requires: filename1, filename2)

IMPORTANT EXECUTION RULES:
- Always start with run_core_analysis_parallel to obtain base components/connections/zones
- For text extraction, prefer extract_text_with_consensus (tool 4) for best accuracy
- Use run_enhancement_analysis_parallel to gather technologies/classification/annotations together before deeper reasoning
- Call enhancement tools (6-8) only if you need to re-run a specific one
- Use quality assessment (tool 14) before analysis for complex or unclear images
- Export tools (16-18) require JSON inputs from previous analysis
- Export tools (16-18) require JSON inputs from previous analysis

CRITICAL PRE-CONDITION:
- You CANNOT perform analysis without a file.
- If no file/image is provided in the context, DO NOT call any analysis tools.
- Instead, politely ask the user to provide an image or file to analyze.
""",
    tools=[
        # Core analysis bundle - using FunctionTool instead of LongRunningFunctionTool
        # to workaround A2A task completion issue
        FunctionTool(func=vision_analysis.run_core_analysis_parallel),
        # OCR & Text
        FunctionTool(func=vision_analysis.extract_text_from_image),
        FunctionTool(func=vision_analysis.extract_text_with_paddleocr),
        FunctionTool(func=vision_analysis.extract_text_with_consensus),
        # Enhancement bundle
        FunctionTool(func=vision_analysis.run_enhancement_analysis_parallel),
        # Enhancement
        FunctionTool(func=vision_analysis.detect_technologies),
        FunctionTool(func=vision_analysis.classify_diagram_type),
        FunctionTool(func=vision_analysis.extract_annotations),
        # Analysis
        FunctionTool(func=vision_analysis.analyze_layout),
        FunctionTool(func=vision_analysis.analyze_styling),
        FunctionTool(func=vision_analysis.infer_relationships),
        # Quality
        FunctionTool(func=vision_analysis.validate_visual_analysis),
        FunctionTool(func=vision_analysis.enhance_analysis),
        FunctionTool(func=vision_analysis.assess_image_quality),
        # Export
        FunctionTool(func=vision_analysis.export_to_plantuml),
        FunctionTool(func=vision_analysis.export_to_mermaid),
        FunctionTool(func=vision_analysis.export_to_drawio),
        # Advanced Vision
        FunctionTool(func=vision_analysis.extract_legend_mappings),
        FunctionTool(func=vision_analysis.detect_line_crossings),
        FunctionTool(func=vision_analysis.detect_trust_boundaries),
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
1. visual_analyzer - Performs visual analysis using tools (and uses run_core_analysis_parallel to fetch components/connections/zones together)
2. merge_visual_analysis - Merges visual analysis results into unified representation

Workflow:
- For visual analysis: Delegate to visual_analyzer (it uses run_core_analysis_parallel to gather core data up front)
- For merging results: Delegate to merge_visual_analysis
- You do not touch sub-agent's input or output, you only delegate to them.

IMPORTANT GUARDRAILS:
- If the user is just saying hello or asking a general question NOT related to analyzing a specific image/file, YOU should respond directly with a brief reply.
- ONLY delegate to tools if the user has provided a file/image or is explicitly asking to analyze a previously provided one.
- NEVER call any tools when filename/session_id/user_id are missing or unknown. When unsure, do not call tools; ask for an image instead.
- If no file is present, ask the user to provide one and stop. Do not attempt quality assessment with placeholder values.""",
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
