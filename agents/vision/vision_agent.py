"""
Vision Agent - Main entry point using ADK SDK
"""
import os
import logging
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
import uvicorn
from google.adk.planners import plan_re_act_planner
from fastapi.middleware.cors import CORSMiddleware
from google.adk_community.models.openai_llm import OpenAI
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.artifacts import FileArtifactService
from vision_analysis import VisionAnalysis
from prompts import get_merger_instructions

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_name = "vision-agent"
# Initialize vision agent
artifact_service = FileArtifactService(root_dir=os.getenv("ARTIFACT_ROOT_DIR", "./my_artifacts"))
# Use postgresql+psycopg:// for async driver (psycopg 3.x)
db_url = os.getenv("DATABASE_URL", "postgresql://admin:admin123@localhost:5432/agent_platform")
# Convert postgresql:// to postgresql+psycopg:// for async support
if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
session_service = DatabaseSessionService(db_url=db_url)
vision_analysis = VisionAnalysis(artifact_service)

# Create vision analysis agent with multiple tools that can run in parallel
visual_analysis_agent = Agent(
    name="visual_analyzer",
    description="Specialized agent for analyzing visual elements from images with advanced capabilities",
    model=OpenAI(model="gpt-5.1"),
    instruction="""You are an advanced visual analysis agent specialized in analyzing diagrams and images.

You have multiple tools available for comprehensive analysis:

CORE ANALYSIS TOOLS (call in parallel for complete analysis):
1. analyze_visual_components - Extracts visual components (nodes, boxes, icons, etc.)
2. analyze_visual_connections - Extracts visual connections (arrows, lines, etc.)
3. analyze_visual_zones - Extracts visual zones (regions, boundaries, etc.)

OCR & TEXT EXTRACTION (accurate text recognition):
4. extract_text_from_image - Extracts text using GPT
5. extract_text_with_paddleocr - Extracts text using PaddleOCR (more accurate)
6. extract_text_with_consensus - Uses both GPT and PaddleOCR for best results

ENHANCEMENT TOOLS:
7. detect_technologies - Identifies technologies, cloud services, frameworks
8. classify_diagram_type - Classifies diagram type, notation, and style
9. extract_annotations - Extracts notes, callouts, warnings

ANALYSIS TOOLS (for deeper understanding):
10. analyze_layout - Analyzes layout structure and hierarchy
11. analyze_styling - Analyzes color coding and visual conventions
12. infer_relationships - Infers logical relationships not shown visually

QUALITY TOOLS (require analysis results as input):
13. validate_visual_analysis - Validates analysis quality (requires: components_json, connections_json, zones_json)
14. enhance_analysis - Enhances initial analysis (requires: initial_analysis_json)
15. assess_image_quality - Assesses image quality before analysis

ADVANCED ANALYSIS:
16. identify_regions - Identifies logical regions in complex diagrams
17. analyze_by_regions - Region-based analysis for complex diagrams
18. iterative_analysis - Iterative refinement with quality threshold (requires: max_iterations)

EXPORT TOOLS (require analysis results):
19. export_to_plantuml - Converts analysis to PlantUML code (requires: components_json, connections_json, zones_json)
20. export_to_mermaid - Converts analysis to Mermaid code (requires: components_json, connections_json, zones_json)
21. export_to_drawio - Converts analysis to draw.io XML (requires: components_json, connections_json, zones_json)

ADVANCED VISION TOOLS:
22. extract_legend_mappings - Extract and parse diagram legends
23. detect_line_crossings - Detect line crossings vs actual intersections (requires: connections_json)
24. detect_trust_boundaries - Identify security/trust boundaries (optional: components_json)

COMPARISON TOOLS:
25. compare_diagrams - Compares two diagrams (requires: filename1, filename2)

IMPORTANT EXECUTION RULES:
- For comprehensive analysis, FIRST call core tools (1-3) in PARALLEL
- For text extraction, prefer extract_text_with_consensus (tool 6) for best accuracy
- Call enhancement tools (7-9) in PARALLEL for additional insights
- Use quality assessment (tool 15) before analysis for complex or unclear images
- Use iterative_analysis (tool 18) for automatic quality improvement
- Use region-based analysis (tool 17) for very complex diagrams
- Export tools (19-21) require JSON inputs from previous analysis
- All tools take user_id, session_id, and filename parameters
""",
    tools=[
        # Core analysis
        vision_analysis.analyze_visual_components,
        vision_analysis.analyze_visual_connections,
        vision_analysis.analyze_visual_zones,
        # OCR & Text
        vision_analysis.extract_text_from_image,
        vision_analysis.extract_text_with_paddleocr,
        vision_analysis.extract_text_with_consensus,
        # Enhancement
        vision_analysis.detect_technologies,
        vision_analysis.classify_diagram_type,
        vision_analysis.extract_annotations,
        # Analysis
        vision_analysis.analyze_layout,
        vision_analysis.analyze_styling,
        vision_analysis.infer_relationships,
        # Quality
        vision_analysis.validate_visual_analysis,
        vision_analysis.enhance_analysis,
        vision_analysis.assess_image_quality,
        # Advanced
        vision_analysis.identify_regions,
        vision_analysis.analyze_by_regions,
        vision_analysis.iterative_analysis,
        # Export
        vision_analysis.export_to_plantuml,
        vision_analysis.export_to_mermaid,
        vision_analysis.export_to_drawio,
        # Advanced Vision
        vision_analysis.extract_legend_mappings,
        vision_analysis.detect_line_crossings,
        vision_analysis.detect_trust_boundaries,
        # Comparison
        vision_analysis.compare_diagrams,
    ],
    planner=plan_re_act_planner.PlanReActPlanner()
)

merger = Agent(
    name="merge_visual_analysis",
    description="Specialized sub-agent for merging visual analysis results into unified representation",
    model=OpenAI(model="gpt-5.1"),
    instruction=get_merger_instructions(),
)

# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=agent_name.replace("-", "_"),
    description="Specialized agent for visual analysis of diagrams and images.",
    model=OpenAI(model="gpt-5.1"),
    instruction="""For visual analysis tasks, you have two sub-agents:
1. visual_analyzer - Performs visual analysis using tools (components, connections, zones)
2. merge_visual_analysis - Merges visual analysis results into unified representation

Workflow:
- For visual analysis: Delegate to visual_analyzer (it will call all tools in parallel)
- For merging results: Delegate to merge_visual_analysis
- You do not touch sub-agent's input or output, you only delegate to them.""",
    sub_agents=[visual_analysis_agent, merger],
    planner=plan_re_act_planner.PlanReActPlanner()
)

app = to_a2a(
    agent=root_agent,
    port=8002,
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

