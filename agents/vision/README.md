# Vision Agent

Advanced visual analysis agent for architecture diagrams and images using GPT Vision and multi-tool analysis.

## Features

### Core Analysis (3 tools)
- **Visual Components** - Extract components (nodes, boxes, icons, etc.)
- **Visual Connections** - Extract connections (arrows, lines, etc.)
- **Visual Zones** - Extract zones (regions, boundaries, etc.)

### OCR & Text Extraction (3 tools)
- **GPT OCR** - Standard text extraction
- **PaddleOCR** - High-accuracy dedicated OCR (fallback to GPT)
- **Consensus Extraction** - Combines both for best results

### Enhancement Tools (3 tools)
- **Technology Detection** - Identify cloud services, frameworks, tools
- **Diagram Classification** - Classify diagram type and notation
- **Annotation Extraction** - Extract notes, callouts, warnings

### Analysis Tools (3 tools)
- **Layout Analysis** - Analyze structure and hierarchy
- **Styling Analysis** - Analyze color coding and conventions
- **Relationship Inference** - Infer logical relationships

### Quality Tools (3 tools)
- **Quality Assessment** - Evaluate image quality
- **Validation** - Check analysis quality and consistency
- **Enhancement** - Improve analysis iteratively

### Advanced Analysis (3 tools)
- **Region Identification** - Identify logical regions
- **Region-based Analysis** - Detailed analysis per region
- **Iterative Analysis** - Auto-improve with quality threshold

### Export Tools (2 tools)
- **PlantUML Export** - Generate PlantUML code
- **Mermaid Export** - Generate Mermaid diagram code

### Comparison (1 tool)
- **Diagram Comparison** - Compare two diagrams

## Installation

### Using Docker (Recommended)

```bash
# Build the image
docker build -t vision-agent .

# Run the container
docker run -p 8002:8002 \
  -e DATABASE_URL=postgresql://admin:admin123@db:5432/agent_platform \
  -e OPENAI_API_KEY=your_key_here \
  -v $(pwd)/my_artifacts:/app/my_artifacts \
  vision-agent
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run the agent
python vision_agent.py
```

## Usage

### Basic Workflow

```python
# The agent runs on port 8002 as an A2A service
# You can call it from the orchestrator or directly via A2A protocol

# Example: Analyze an image
{
  "user_id": "user123",
  "session_id": "session456",
  "filename": "architecture_diagram.png"
}
```

### Export to PlantUML

```python
# First analyze, then export
# 1. Run analysis to get components, connections, zones
# 2. Export to PlantUML
{
  "tool": "export_to_plantuml",
  "user_id": "user123",
  "session_id": "session456",
  "filename": "diagram.png",
  "components_json": "...",
  "connections_json": "...",
  "zones_json": "..."
}
```

## Configuration

See `.env.example` for all configuration options.

### Required
- `OPENAI_API_KEY` - Your OpenAI API key for GPT
- `DATABASE_URL` - PostgreSQL connection string

### Optional
- `ARTIFACT_ROOT_DIR` - Path for storing artifacts (default: `./my_artifacts`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Architecture

```
vision/
├── __init__.py           # Package initialization
├── models.py             # Pydantic models (24 models)
├── prompts.py            # Analysis instructions (13 prompts)
├── vision_analysis.py    # Core analysis logic (22 methods)
├── vision_agent.py       # A2A agent entry point
├── requirements.txt      # Python dependencies
├── Dockerfile            # Container configuration
└── README.md            # This file
```

## API

The agent exposes 21 tools via A2A protocol on port 8002.

### Tool Categories

**Core**: `analyze_visual_components`, `analyze_visual_connections`, `analyze_visual_zones`

**OCR**: `extract_text_from_image`, `extract_text_with_paddleocr`, `extract_text_with_consensus`

**Enhancement**: `detect_technologies`, `classify_diagram_type`, `extract_annotations`

**Analysis**: `analyze_layout`, `analyze_styling`, `infer_relationships`

**Quality**: `assess_image_quality`, `validate_visual_analysis`, `enhance_analysis`

**Advanced**: `identify_regions`, `analyze_by_regions`,

**Export**: `export_to_plantuml`, `export_to_mermaid` , `export_to_drawio`

**Comparison**: `compare_diagrams`

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .
```

## License

Part of the Agent Platform project.

