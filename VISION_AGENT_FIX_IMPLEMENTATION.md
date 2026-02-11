# Vision Agent Fix - Implementation Guide

## Problems Identified
1. ✗ Missing visual details that downstream agents need
2. ✗ Too slow (22 tools causing confusion)
3. ✗ Calling wrong tools or skipping important ones
4. ✗ Output too vague (generic descriptions)
5. ✗ Output too noisy (irrelevant details)

## Solution Overview
- **Reduce:** 22 → 12 tools (remove non-extraction tools)
- **Enhance:** Extract MORE visual detail in core tools
- **Clarify:** Improve prompts to be more specific about what to extract
- **Simplify:** Clear workflow so agent knows what to call

---

## STEP 1: Remove 7 Non-Extraction Tools

### Tools to Remove from vision_agent.py

**Lines 149-152: Export tools (don't extract, they transform)**
```python
# REMOVE THESE:
FunctionTool(func=vision_analysis.export_to_plantuml),
FunctionTool(func=vision_analysis.export_to_mermaid),
FunctionTool(func=vision_analysis.export_to_drawio),
```

**Lines 145-146: Meta-analysis tools (overhead, don't extract new info)**
```python
# REMOVE THESE:
FunctionTool(func=vision_analysis.validate_visual_analysis),
FunctionTool(func=vision_analysis.enhance_analysis),
```

**Lines 132-133: Fake PaddleOCR tools (not implemented, text already in text_content)**
```python
# REMOVE THESE:
FunctionTool(func=vision_analysis.extract_text_with_paddleocr),
FunctionTool(func=vision_analysis.extract_text_with_consensus),
```

**Line 147: Quality assessment (pre-analysis overhead, doesn't extract diagram info)**
```python
# REMOVE THIS:
FunctionTool(func=vision_analysis.assess_image_quality),
```

### Tools to KEEP (12 tools)

```python
tools=[
    # CORE EXTRACTION (3 tools)
    FunctionTool(func=vision_analysis.run_core_analysis_parallel),      # components, connections, zones
    FunctionTool(func=vision_analysis.run_enhancement_analysis_parallel), # technologies, annotations
    FunctionTool(func=vision_analysis.extract_boundaries),               # boundaries (rename from detect_trust_boundaries)

    # TEXT EXTRACTION (1 tool)
    FunctionTool(func=vision_analysis.extract_text_from_image),

    # RELATIONSHIP ANALYSIS (1 tool)
    FunctionTool(func=vision_analysis.infer_relationships),

    # LAYOUT & STRUCTURE (2 tools)
    FunctionTool(func=vision_analysis.analyze_layout),
    FunctionTool(func=vision_analysis.analyze_styling),

    # ADVANCED VISUAL (3 tools)
    FunctionTool(func=vision_analysis.extract_legend_mappings),
    FunctionTool(func=vision_analysis.detect_line_crossings),
    FunctionTool(func=vision_analysis.identify_regions),

    # COMPARISON (1 tool) - optional, could remove if not needed
    FunctionTool(func=vision_analysis.compare_diagrams),
]
```

**Result:** 22 → 12 tools

---

## STEP 2: Enhance Models to Capture More Visual Detail

### File: agents/vision/models.py

#### Update VisualComponent (lines 15-33)

**ADD these fields after line 29 (after visual_group):**

```python
class VisualComponent(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    name: str
    component_type: Literal[...]
    visual_type: Literal[...]
    position: Position
    text_content: str
    visual_group: str

    # ADD THESE NEW FIELDS:
    primary_color: str = Field(
        default="",
        description="Main color of the component (red, blue, green, orange, gray, black, etc.)"
    )
    border_style: str = Field(
        default="",
        description="Border style: solid, dashed, dotted, double, thick, none"
    )
    visual_badges: List[str] = Field(
        default_factory=list,
        description="Visual icons, symbols, badges visible on or near component: lock icon, warning symbol, cloud logo, star, checkmark, etc."
    )
    all_text_labels: List[str] = Field(
        default_factory=list,
        description="ALL text visible on or near this component, including labels, annotations, notes"
    )
    size_category: Literal["very_small", "small", "medium", "large", "very_large"] = Field(
        default="medium",
        description="Relative size compared to other components"
    )

    confidence: confloat(ge=0.0, le=1.0) = Field(...)
```

#### Update VisualConnection (lines 35-48)

**ADD these fields after line 44 (after labels):**

```python
class VisualConnection(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    source: str
    target: str
    connection_type: Literal[...]
    direction: Literal[...]
    labels: List[str]

    # ADD THESE NEW FIELDS:
    color: str = Field(
        default="black",
        description="Color of the connection line (red, blue, green, orange, black, gray, etc.)"
    )
    thickness: Literal["very_thin", "thin", "normal", "thick", "very_thick"] = Field(
        default="normal",
        description="Visual thickness/weight of the line"
    )
    line_pattern: str = Field(
        default="solid",
        description="Line pattern: solid, small-dashes, large-dashes, dots, dot-dash"
    )
    visual_markers: List[str] = Field(
        default_factory=list,
        description="Icons or symbols ON the connection line: lock icon, warning, number badge, etc."
    )
    all_text_labels: List[str] = Field(
        default_factory=list,
        description="ALL text on or near the connection (protocols, data types, annotations, notes)"
    )

    confidence: confloat(ge=0.0, le=1.0) = Field(...)
```

#### Rename TrustBoundary to VisualBoundary (lines 385-404)

**REPLACE the entire TrustBoundary class:**

```python
# OLD NAME: TrustBoundary
# NEW NAME: VisualBoundary
class VisualBoundary(BaseModel):
    """Generic visual boundary/enclosure extracted from diagram"""
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    boundary_name: str = Field(
        ...,
        description="Text label on or near the boundary (exact text as shown)"
    )
    visual_style: str = Field(
        ...,
        description="Visual appearance description: 'dashed red line', 'thick blue border', 'shaded gray region'"
    )
    color: str = Field(
        ...,
        description="Primary color of the boundary (red, blue, green, orange, gray, black)"
    )
    line_style: Literal["solid", "dashed", "dotted", "double", "other"] = Field(
        ...,
        description="Style of the boundary line"
    )
    shape: Literal["rectangle", "rounded_rectangle", "circle", "ellipse", "cloud", "irregular", "other"] = Field(
        ...,
        description="Overall shape of the boundary"
    )
    text_labels: List[str] = Field(
        default_factory=list,
        description="ALL text written on or near this boundary"
    )
    components_inside: List[str] = Field(
        default_factory=list,
        description="Names of components visually enclosed by this boundary"
    )
    position: Position
    confidence: confloat(ge=0.0, le=1.0)
```

**Why this matters:**
- Removes domain-specific fields like `security_level`, `protection_mechanisms`
- Adds pure visual descriptors: `visual_style`, `color`, `line_style`, `shape`
- Downstream agents interpret `text_labels` (cyber agent sees "DMZ", art agent sees "Gallery Wing")

---

## STEP 3: Update Prompts to Extract More Detail

### File: agents/vision/prompts.py

#### Update Component Analysis Prompt (lines 1-102)

**REPLACE get_component_analysis_instructions() with:**

```python
def get_component_analysis_instructions() -> str:
    return """
You are an advanced image analysis model specialized in extracting visual information from diagrams.

Your task:
Given an input image, detect ALL meaningful visual components (nodes/blocks/icons/shapes) and return them as a JSON array of VisualComponent objects.

For EACH component, extract complete visual information:

name:
A short, human-readable identifier from text near or inside the component.
Examples: "User Service", "Postgres DB", "API Gateway", "Load Balancer"

component_type:
Semantic role/type of the component:
- "application" - Applications, services, APIs, microservices
- "service" - Backend services, workers, processors
- "database" - Databases, data stores
- "cache" - Cache layers (Redis, Memcached)
- "queue" - Message queues, event streams
- "api_gateway" - API gateways, reverse proxies
- "load_balancer" - Load balancers, traffic managers
- "storage" - File storage, object storage, blob storage
- "network" - Network devices, routers, switches
- "security" - Security devices, firewalls, WAFs
- "monitoring" - Monitoring, logging, observability
- "user" - Users, clients, actors
- "external_service" - Third-party services, external APIs
- "other" - Anything else

visual_type:
Shape/style of the component:
- "box" - Rectangles, rounded rectangles, squares
- "circle" - Circles, ellipses, ovals
- "icon" - Logos or icons without geometric container
- "diamond" - Diamond/rhombus shapes
- "cylinder" - Database cylinder shape
- "cloud" - Cloud-shaped components
- "other" - Any other shape

position:
Bounding box coordinates: {x, y, width, height}

text_content:
ALL text INSIDE the component box/shape, exactly as shown.
Include every line of text within the component boundary.

visual_group:
Name of the logical group or container this component belongs to.
Examples: "VPC A", "Frontend", "Backend", "Internal Network", "DMZ", "Europe Region"
If no visible group, use empty string "".

primary_color:
Main color of the component.
Examples: "red", "blue", "green", "orange", "gray", "black", "white", "yellow", "purple"
If black/white/grayscale, specify "gray" or "black" or "white".

border_style:
The component's border style.
Options: "solid", "dashed", "dotted", "double", "thick", "none"

visual_badges:
ALL icons, symbols, badges, decorations visible ON or IMMEDIATELY NEXT TO the component.
Extract every visual marker you see:
- Icons: "lock icon", "shield icon", "cloud logo", "database icon", "user icon", "gear icon"
- Symbols: "warning triangle", "checkmark", "X mark", "star", "question mark"
- Badges: "number badge", "red dot", "green dot", "status indicator"
- Status: "offline indicator", "error symbol", "success checkmark"

Examples:
- Component with a small lock icon in corner → ["lock icon"]
- Component with warning triangle and red dot → ["warning triangle", "red dot"]
- Component with AWS logo and shield → ["AWS cloud logo", "shield icon"]

all_text_labels:
ALL text visible OUTSIDE but NEAR the component (annotations, labels, notes).
Do NOT duplicate text_content (text inside). Only capture surrounding text.

Examples:
- If component box says "API Server" (inside) and has "Port 8080" written next to it (outside),
  then text_content="API Server", all_text_labels=["Port 8080"]
- If component has notes like "Legacy system" or "To be migrated" nearby,
  add those to all_text_labels

size_category:
Relative size compared to other components in the diagram.
Options: "very_small", "small", "medium", "large", "very_large"

confidence:
Your confidence score (0.0-1.0) that:
- Component is correctly detected
- component_type classification is appropriate
- Visual details are accurate

IMPORTANT INSTRUCTIONS:
1. Extract ALL visible components, not just a few examples
2. Do NOT include arrows, lines, or connectors as components
3. Capture EVERY visual detail - colors, icons, symbols, text
4. Be specific with colors and visual markers
5. If role/type is unclear, pick closest type and lower confidence

Return ONLY valid JSON: a top-level array of VisualComponent objects with no extra commentary.

Example structure (not exhaustive):
[
  {
    "name": "User Service",
    "component_type": "application",
    "visual_type": "box",
    "position": {"x": 120, "y": 200, "width": 260, "height": 100},
    "text_content": "User Service\\nNode.js",
    "visual_group": "Backend",
    "primary_color": "blue",
    "border_style": "solid",
    "visual_badges": ["lock icon", "cloud logo"],
    "all_text_labels": ["Port 3000", "REST API"],
    "size_category": "medium",
    "confidence": 0.94
  },
  {
    "name": "Postgres DB",
    "component_type": "database",
    "visual_type": "cylinder",
    "position": {"x": 450, "y": 210, "width": 140, "height": 120},
    "text_content": "PostgreSQL\\n14.2",
    "visual_group": "Backend",
    "primary_color": "gray",
    "border_style": "solid",
    "visual_badges": ["database icon"],
    "all_text_labels": ["Primary DB", "Replicated"],
    "size_category": "medium",
    "confidence": 0.97
  }
]
"""
```

#### Update Connection Analysis Prompt (lines 105-191)

**REPLACE get_connection_analysis_instructions() with:**

```python
def get_connection_analysis_instructions() -> str:
    return """
You are an advanced image analysis model specialized in extracting visual connections from diagrams.

Your task:
Extract ALL visual connections (arrows, lines, connectors) between elements in the image.
Return a JSON array of VisualConnection objects.

For EACH connection, extract complete visual information:

source:
Name of the element where the connection starts.
Use the visible text or a descriptive identifier.

target:
Name of the element where the connection ends.

connection_type:
Visual style of the connection:
- "arrow" - Line with arrowhead (solid line + arrow)
- "line" - Simple solid line without arrowheads
- "dotted" - Dotted line
- "dashed" - Dashed line
- "thick" - Noticeably thicker line
- "bidirectional" - Arrows at both ends
- "other" - Any other style

direction:
Flow direction:
- "unidirectional" - Clear arrow from source → target
- "bidirectional" - Arrows at both ends or clearly two-way
- "unknown" - No arrowheads or unclear direction

labels:
Primary text labels directly ON the connection line.
Examples: "HTTPS", "REST", "gRPC", "SQL", "Publishes", "Subscribes"

color:
Color of the connection line.
Examples: "black", "red", "blue", "green", "orange", "gray"
If not clearly colored, use "black".

thickness:
Visual weight of the line:
Options: "very_thin", "thin", "normal", "thick", "very_thick"

line_pattern:
Detailed pattern of the line:
Examples: "solid", "small-dashes", "large-dashes", "dots", "dot-dash", "double-line"

visual_markers:
Icons, symbols, badges ON the connection line itself.
Examples:
- "lock icon" - Security/encryption indicator
- "warning symbol" - Alert or caution
- "number badge" - Sequence numbers
- "checkmark" - Success indicator
- "X mark" - Error indicator

all_text_labels:
EVERY piece of text visible on or near the connection.
Capture ALL labels, annotations, notes, data types, protocols, methods.

Examples:
- Connection with "HTTPS", "443", "JSON", "REST" → capture ALL in all_text_labels
- Connection with note "Async call" → add to all_text_labels
- Connection with "Retry logic: 3x" → add to all_text_labels

confidence:
Your confidence score (0.0-1.0) that:
- Connection exists between source and target
- Visual details are accurate
- source/target pairing is correct

IMPORTANT INSTRUCTIONS:
1. Extract ALL connections, not just primary ones
2. Capture EVERY visual detail - colors, patterns, thickness, markers
3. Extract EVERY piece of text on or near the connection
4. Be specific about line styles and patterns
5. Include even subtle visual markers

Return ONLY valid JSON: a top-level array of VisualConnection objects with no extra commentary.

Example structure:
[
  {
    "source": "Login Form",
    "target": "Authentication Service",
    "connection_type": "arrow",
    "direction": "unidirectional",
    "labels": ["POST /login"],
    "color": "blue",
    "thickness": "normal",
    "line_pattern": "solid",
    "visual_markers": ["lock icon"],
    "all_text_labels": ["POST /login", "HTTPS", "JSON payload", "443"],
    "confidence": 0.95
  },
  {
    "source": "API Gateway",
    "target": "User Service",
    "connection_type": "arrow",
    "direction": "bidirectional",
    "labels": ["REST API"],
    "color": "green",
    "thickness": "thick",
    "line_pattern": "solid",
    "visual_markers": [],
    "all_text_labels": ["REST API", "HTTP/2", "Load balanced"],
    "confidence": 0.92
  }
]
"""
```

#### Update Trust Boundary → Visual Boundary Prompt (lines 1033-1087)

**REPLACE get_trust_boundary_detection_instructions() with get_boundary_extraction_instructions():**

```python
def get_boundary_extraction_instructions() -> str:
    return """
You are a visual boundary extraction specialist.

Your task:
Extract ALL visual boundaries, enclosures, and grouping regions in the diagram.

A visual boundary is any line, border, box, shaded region, or enclosure that groups components together.

For EACH boundary, extract complete visual information:

boundary_name:
The text label visible on or near the boundary (extract exact text as shown).
Examples: "DMZ", "VPC-A", "Backend Services", "Phase 1", "Accounting Dept", "Public Zone"

visual_style:
Plain-language description of the visual appearance.
Examples:
- "dashed red line"
- "thick blue border"
- "light gray shaded region"
- "orange dotted rectangle"
- "double black line"
- "cloud-shaped blue boundary with dashed outline"

color:
Primary color of the boundary line or shading.
Examples: "red", "blue", "gray", "orange", "green", "black", "yellow"

line_style:
Style of the boundary line.
Options: "solid", "dashed", "dotted", "double", "other"

shape:
Overall shape of the boundary.
Options: "rectangle", "rounded_rectangle", "circle", "ellipse", "cloud", "irregular", "other"

text_labels:
ALL text written ON the boundary or NEAR it.
Extract every piece of text including:
- Boundary name/title
- Annotations, notes, comments
- Technical labels, identifiers
- Zone descriptions
- Any other readable text

components_inside:
List of component names visually enclosed by this boundary.
Include all components whose centers are inside the boundary region.

position:
Bounding box coordinates of the boundary region: {x, y, width, height}

confidence:
Your confidence score (0.0-1.0) that:
- Boundary is correctly detected
- Components inside are correctly identified
- Visual details are accurate

CRITICAL RULES:
1. Do NOT interpret what the boundary represents - only describe what you see
2. Extract visual facts only, no domain interpretation
3. Capture every text label visible on or near the boundary
4. Be specific about colors, line styles, and visual appearance

Examples of CORRECT extraction (pure visual facts):
✓ boundary_name="DMZ", color="red", line_style="dashed", text_labels=["DMZ", "Public Access Zone"]
✓ boundary_name="Backend", color="blue", line_style="solid", shape="rounded_rectangle"
✓ visual_style="thick orange dashed line forming an irregular boundary"

Examples of INCORRECT extraction (interpretation):
✗ "Security boundary protecting sensitive data" - this is interpretation
✗ "Trust zone requiring authentication" - this is interpretation
✗ "DMZ providing defense in depth" - this is interpretation

Return ONLY valid JSON: a top-level array of VisualBoundary objects with no extra commentary.

Example structure:
[
  {
    "boundary_name": "DMZ",
    "visual_style": "dashed red line with thick border",
    "color": "red",
    "line_style": "dashed",
    "shape": "rectangle",
    "text_labels": ["DMZ", "Demilitarized Zone", "Public Access"],
    "components_inside": ["Web Server", "Load Balancer", "WAF"],
    "position": {"x": 100, "y": 200, "width": 500, "height": 300},
    "confidence": 0.93
  },
  {
    "boundary_name": "VPC-Production",
    "visual_style": "thick blue solid border with light blue shading",
    "color": "blue",
    "line_style": "solid",
    "shape": "rounded_rectangle",
    "text_labels": ["VPC-Production", "10.0.0.0/16", "AWS us-east-1"],
    "components_inside": ["API Gateway", "Lambda Functions", "RDS Database"],
    "position": {"x": 50, "y": 400, "width": 700, "height": 400},
    "confidence": 0.96
  }
]
"""
```

---

## STEP 4: Update Function Names

### File: agents/vision/vision_analysis.py

**Line 1648: Rename function**

```python
# OLD:
async def detect_trust_boundaries(...)

# NEW:
async def extract_boundaries(...)
```

**Lines 1683, 1696: Update prompt function call**

```python
# OLD:
system_instruction=get_trust_boundary_detection_instructions(),

# NEW:
system_instruction=get_boundary_extraction_instructions(),
```

**Line 1702: Update model reference**

```python
# OLD:
llm_request.set_output_schema(TrustBoundary)

# NEW:
llm_request.set_output_schema(VisualBoundary)
```

### File: agents/vision/prompts.py

**Line 1033: Rename function**

```python
# OLD:
def get_trust_boundary_detection_instructions() -> str:

# NEW:
def get_boundary_extraction_instructions() -> str:
```

### File: agents/vision/vision_agent.py

**Line 155: Update tool name**

```python
# OLD:
FunctionTool(func=vision_analysis.detect_trust_boundaries),

# NEW:
FunctionTool(func=vision_analysis.extract_boundaries),
```

**Lines 66-125: Update agent instructions**

Update the instruction to reflect the new tool name and simplified workflow:

```python
instruction="""You are an advanced visual analysis agent specialized in extracting visual information from diagrams.

WORKFLOW:
1. run_core_analysis_parallel - Extract components, connections, zones (ALWAYS START HERE)
2. run_enhancement_analysis_parallel - Extract technologies, annotations
3. extract_boundaries - Extract visual boundaries and enclosures
4. infer_relationships - Infer logical relationships between components

ADDITIONAL TOOLS (use as needed):
- extract_text_from_image - Extract all text (if core analysis missed text)
- analyze_layout - Analyze layout structure and hierarchy
- analyze_styling - Analyze color patterns and visual conventions
- extract_legend_mappings - Extract legend symbols and meanings
- detect_line_crossings - Analyze line topology (advanced)
- identify_regions - Segment complex diagrams (advanced)
- compare_diagrams - Compare two diagrams (requires 2 files)

CRITICAL RULES:
1. You are a VISUAL EXTRACTOR - you describe what you SEE, not what it means
2. Extract colors, shapes, text, positions, visual markers
3. Do NOT interpret domain meaning (security, business, art, cooking, etc.)
4. Downstream agents will interpret the visual facts you provide

WORKFLOW EXAMPLE:
User: "Analyze this architecture diagram"
1. Call run_core_analysis_parallel → get components, connections, zones
2. Call run_enhancement_analysis_parallel → get technologies, annotations
3. Call extract_boundaries → get visual boundaries
4. Return all extracted visual data

IMPORTANT:
- If no file is provided, ask for one
- NEVER call tools without required parameters
- NEVER interpret what components mean (e.g., don't say "this is a security zone")
- ALWAYS extract visual facts objectively
"""
```

---

## STEP 5: Update CyberSecurity Agent to Use New Field Names

### File: agents/cybersecurity/modules/architecture_analysis.py

**Update line 35 parameter name:**

```python
# OLD:
trust_boundaries_json: str,

# NEW:
boundaries_json: str,  # Renamed from trust_boundaries_json
```

**Update lines 65-66:**

```python
# OLD:
self._validate_json_input("trust_boundaries", trust_boundaries_json)

# NEW:
self._validate_json_input("boundaries", boundaries_json)
```

**Update line 75 parameter:**

```python
# OLD:
trust_boundaries_json,

# NEW:
boundaries_json,
```

**Update lines 189-194 in context string:**

```python
# OLD:
## Trust Boundaries
Security and trust boundaries (DMZ, VPC, network segments):
```json
{trust_boundaries}
```

# NEW:
## Visual Boundaries
Visual boundaries and enclosures (zones, regions, groupings):
```json
{boundaries}
```
```

**Update line 233 in format call:**

```python
# OLD:
trust_boundaries=trust_boundaries_json,

# NEW:
boundaries=boundaries_json,
```

**The CyberSecurity agent will now interpret the visual boundary data:**
- Sees `text_labels=["DMZ", "Public"]` + `color="red"` → interprets as security zone
- Sees `text_labels=["Backend Services"]` + `color="blue"` → interprets as internal zone

---

## STEP 6: Test the Changes

### Create a test script:

```python
# File: test_vision_extraction.py
import asyncio
from agents.vision.vision_analysis import VisionAnalysis
from agents.vision.vision_agent import artifact_service

async def test_vision():
    vision = VisionAnalysis(artifact_service)

    # Test with a sample diagram
    result = await vision.run_core_analysis_parallel(
        user_id="test_user",
        session_id="test_session",
        filename="architecture_diagram.png"
    )

    print("Core Analysis Result:")
    print(result)

    # Check for new fields
    import json
    data = json.loads(result)

    # Check components have new visual fields
    if data['components']:
        comp = data['components'][0]
        print(f"\nSample Component Fields:")
        print(f"  primary_color: {comp.get('primary_color', 'MISSING')}")
        print(f"  visual_badges: {comp.get('visual_badges', 'MISSING')}")
        print(f"  all_text_labels: {comp.get('all_text_labels', 'MISSING')}")

    # Check connections have new visual fields
    if data['connections']:
        conn = data['connections'][0]
        print(f"\nSample Connection Fields:")
        print(f"  color: {conn.get('color', 'MISSING')}")
        print(f"  thickness: {conn.get('thickness', 'MISSING')}")
        print(f"  all_text_labels: {conn.get('all_text_labels', 'MISSING')}")

asyncio.run(test_vision())
```

---

## Summary of Changes

| Issue | Solution | Files Changed |
|-------|----------|---------------|
| #1: Missing visual details | Added color, visual_badges, all_text_labels, thickness, etc. | models.py, prompts.py |
| #2: Too slow (22 tools) | Removed 7 non-extraction tools (22→12) | vision_agent.py |
| #3: Calling wrong tools | Simplified workflow, clearer instructions | vision_agent.py |
| #4: Output too vague | Enhanced prompts to extract MORE detail | prompts.py |
| #5: Output too noisy | Focused on visual facts only, removed interpretation | prompts.py, models.py |

**Before:** 22 tools, vague output, domain interpretation mixed in
**After:** 12 tools, rich visual detail, pure extraction

The Vision agent now outputs **rich visual facts** that ANY downstream agent can interpret:
- **CyberSec agent**: Interprets "DMZ" + red color → security zone
- **Art agent**: Interprets red + dashed → design emphasis
- **Business agent**: Interprets "Phase 1" → process stage
- **Cooking agent**: Ignores architecture diagrams entirely
