# Vision Agent

Advanced visual analysis agent for architecture diagrams and images using GPT Vision and multi-tool analysis.

## Features

### Core Extraction
- **analyze_visual_components** – Extract components (nodes, icons, boxes)
- **analyze_visual_connections** – Extract connections (arrows, lines, link styling)
- **analyze_visual_zones** – Extract zones/regions and their positioning

### OCR
- **extract_text_from_image** – Pull all visible text from the image

### Analysis
- **analyze_layout** – Describe structure and hierarchy
- **analyze_styling** – Capture color, line, and visual conventions
- **validate_visual_analysis** – Sanity-check prior extraction

### Annotations & Boundaries
- **extract_annotations** – Notes, callouts, warnings
- **extract_boundaries** – Visual boundaries/enclosures

### Advanced Visual
- **identify_regions** – Segment complex diagrams
- **extract_legend_mappings** – Map legend symbols to meanings
- **detect_line_crossings** – Flag crossing lines and whether they connect

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

The agent exposes A2A tools on port 8002.

### Tool Categories

**Core**: `analyze_visual_components`, `analyze_visual_connections`, `analyze_visual_zones`

**OCR**: `extract_text_from_image`

**Analysis**: `analyze_layout`, `analyze_styling`, `validate_visual_analysis`

**Annotations**: `extract_annotations`

**Boundaries**: `extract_boundaries`

**Advanced**: `identify_regions`, `extract_legend_mappings`, `detect_line_crossings`

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

