# Vision Agent: Pure Visual Extraction (Domain-Agnostic)

## Core Principle
The Vision agent extracts VISUAL FACTS from images, without interpreting what they mean for any specific domain (security, art, business, etc.).

## Issues to Fix

### 1. Remove Domain-Specific Interpretations from Models

#### ❌ Current: TrustBoundary (lines 385-403 in models.py)
```python
class TrustBoundary(BaseModel):
    boundary_type: Literal["internet_facing", "dmz", "internal_network", ...]  # ← CYBER INTERPRETATION
    security_level: Literal["public", "restricted", "confidential", ...]        # ← INTERPRETATION
    protection_mechanisms: List[str]                                             # ← INTERPRETATION
```

#### ✅ Should Be: VisualBoundary
```python
class VisualBoundary(BaseModel):
    """Pure visual description of a boundary/enclosure in the diagram"""
    boundary_name: str = Field(..., description="Text label on the boundary (exact text)")
    visual_style: str = Field(..., description="Visual appearance: 'dashed red line', 'thick blue border', 'shaded region'")
    color: str = Field(..., description="Primary color of the boundary")
    line_style: Literal["solid", "dashed", "dotted", "double", "other"]
    shape: Literal["rectangle", "rounded_rectangle", "circle", "cloud", "irregular", "other"]
    text_labels: List[str] = Field(default_factory=list, description="ALL text on or near this boundary")
    components_inside: List[str] = Field(default_factory=list, description="Components enclosed")
    position: Position
    confidence: float
```

**How downstream agents use this:**
- **CyberSec agent** sees `text_labels=["DMZ", "Public", "0.0.0.0/0"]` → interprets as security zone
- **Art agent** sees `color="red", line_style="dashed"` → interprets as stylistic choice
- **Business process agent** sees `boundary_name="Phase 1"` → interprets as process stage

### 2. Rename Domain-Specific Tools

| Current Name | Domain Bias | New Name |
|--------------|-------------|----------|
| `detect_trust_boundaries` | Security | `extract_boundaries` |

### 3. Enhance Models to Extract More Visual Detail

All models should capture MORE visual information for ANY agent to interpret:

#### VisualComponent Enhancements
```python
class VisualComponent(BaseModel):
    # Existing fields (keep these)
    name: str
    component_type: Literal[...]
    visual_type: Literal[...]
    position: Position
    text_content: str
    visual_group: str
    confidence: float

    # ADD: More visual detail
    primary_color: str = Field(default="", description="Main color of the component")
    secondary_colors: List[str] = Field(default_factory=list, description="Additional colors")
    visual_decorations: List[str] = Field(
        default_factory=list,
        description="Icons, badges, symbols on/near component: 'lock icon', 'star badge', 'warning triangle'"
    )
    border_style: str = Field(default="", description="Border appearance: 'solid', 'dashed', 'double', 'none'")
    surrounding_text: List[str] = Field(
        default_factory=list,
        description="ALL text labels, annotations, notes near (but not inside) this component"
    )
```

**Prompt Update:**
```
Extract complete visual description:
- primary_color: Main color (red, blue, green, orange, gray, etc.)
- secondary_colors: Any additional colors present
- visual_decorations: ALL icons, symbols, badges visible on or near the component
  Examples: "lock icon", "shield symbol", "checkmark", "warning triangle", "star",
            "number badge", "cloud logo", "database icon", "arrow badge"
- border_style: The component's border (solid, dashed, dotted, double, thick, none)
- surrounding_text: ALL text labels or annotations near (but outside) the component
```

#### VisualConnection Enhancements
```python
class VisualConnection(BaseModel):
    # Existing fields (keep these)
    source: str
    target: str
    connection_type: Literal[...]
    direction: Literal[...]
    labels: List[str]
    confidence: float

    # ADD: More visual detail
    color: str = Field(default="", description="Color of the connection line")
    thickness: Literal["thin", "normal", "thick", "very_thick"] = "normal"
    visual_decorations: List[str] = Field(
        default_factory=list,
        description="Icons, symbols, badges ON the connection line"
    )
    line_pattern: str = Field(default="", description="Visual pattern: 'solid', 'dots', 'dashes', 'dot-dash'")
    all_text: List[str] = Field(
        default_factory=list,
        description="ALL text labels, annotations on or near this connection"
    )
```

**Prompt Update:**
```
Extract complete visual description:
- color: Line color (black, red, green, blue, orange, etc.)
- thickness: Visual weight (thin, normal, thick, very_thick)
- visual_decorations: Icons or symbols ON the line
  Examples: "lock icon", "number badge", "warning symbol", "checkmark"
- line_pattern: The line's pattern (solid, small dots, large dots, small dashes, large dashes, dot-dash)
- all_text: EVERY piece of text on or near the connection (protocols, labels, notes, data types, etc.)
```

### 4. Update Prompts to Remove Interpretation

#### Current `detect_trust_boundaries` Prompt (BEFORE)
```python
def get_trust_boundary_detection_instructions() -> str:
    return """
You are a security trust boundary detection specialist.

Identify security and trust boundaries in architecture diagrams...

Trust boundaries indicate:
- Network segmentation (DMZ, internal, private)           # ← INTERPRETATION
- Security zones (public-facing, restricted, confidential) # ← INTERPRETATION

boundary_type: Classification (internet_facing, dmz, internal_network, etc.)
security_level: public, restricted, confidential, highly_confidential
protection_mechanisms: Security controls (WAF, Firewall, Security Group, etc.)
"""
```

#### New `extract_boundaries` Prompt (AFTER)
```python
def get_boundary_extraction_instructions() -> str:
    return """
You are a visual boundary extraction specialist.

Your task:
Extract all visual boundaries, enclosures, and grouping regions in the diagram.

A visual boundary is any line, border, box, shaded region, or enclosure that groups components together.

For each boundary, extract:

boundary_name: The text label visible on or near the boundary (extract exact text as shown)
  Examples: "DMZ", "VPC-A", "Backend Services", "Phase 1", "Accounting Department"

visual_style: Describe the visual appearance in plain terms
  Examples: "dashed red line", "thick blue border", "light gray shaded region",
            "orange dotted line", "double black line", "cloud-shaped blue boundary"

color: Primary color of the boundary line or shading
  Examples: "red", "blue", "gray", "orange", "green", "black"

line_style: The style of the boundary line
  Options: "solid", "dashed", "dotted", "double", "other"

shape: The overall shape of the boundary
  Options: "rectangle", "rounded_rectangle", "circle", "ellipse", "cloud", "irregular", "other"

text_labels: ALL text written on the boundary or near it
  Extract every piece of text, including:
  - Boundary name/title
  - Annotations, notes, comments
  - Technical labels, identifiers
  - Any other readable text

components_inside: List of component names that are visually enclosed by this boundary

position: Bounding box coordinates of the boundary region

CRITICAL: Do NOT interpret what the boundary represents or means. Only describe what you see visually.

Examples of CORRECT extraction (visual facts only):
✓ "Dashed red line labeled 'DMZ' enclosing components A, B, C"
✓ "Thick blue border with text 'Private Subnet' containing components X, Y"
✓ "Light gray shaded region labeled 'Backend' with 5 components inside"

Examples of INCORRECT extraction (interpretation):
✗ "Security zone separating public from private components"
✗ "Trust boundary protecting sensitive data"
✗ "DMZ providing defense in depth"

Output only valid JSON array of VisualBoundary objects, no extra text.
"""
```

### 5. Tool Reduction (Still Valid)

Remove tools that don't extract visual information:

**Remove (7 tools):**
- ❌ `export_to_plantuml/mermaid/drawio` (3) - Transform data, don't extract
- ❌ `enhance_analysis` - Meta-analysis
- ❌ `validate_visual_analysis` - Meta-analysis
- ❌ `extract_text_with_paddleocr/consensus` (2) - Not implemented, text already captured

**Final tool count: 22 → 15 tools**

### 6. Tools to Keep (Domain-Agnostic Visual Extraction)

1. ✅ `run_core_analysis_parallel` - Extract components, connections, zones
2. ✅ `run_enhancement_analysis_parallel` - Extract technologies, annotations
3. ✅ `extract_boundaries` (rename from detect_trust_boundaries)
4. ✅ `infer_relationships` - Logical relationships (useful for any domain)
5. ✅ `extract_legend_mappings` - Symbol-to-meaning mappings
6. ✅ `analyze_layout` - Structural organization
7. ✅ `analyze_styling` - Color/style patterns
8. ✅ `extract_text_from_image` - Text extraction
9. ✅ `detect_line_crossings` - Line topology
10. ✅ `identify_regions` - Region segmentation
11. ✅ `compare_diagrams` - Visual comparison

All of these extract or describe visual facts without domain interpretation.

## Example: How Different Agents Use the Same Visual Data

### Vision Agent Extracts (Pure Visual Facts):
```json
{
  "boundary_name": "DMZ",
  "visual_style": "dashed red line",
  "color": "red",
  "line_style": "dashed",
  "shape": "rectangle",
  "text_labels": ["DMZ", "Demilitarized Zone", "Public Access"],
  "components_inside": ["Web Server", "Load Balancer", "WAF"],
  "position": {"x": 100, "y": 200, "width": 500, "height": 300}
}
```

### CyberSecurity Agent Interprets:
- `text_labels=["DMZ", "Public Access"]` → This is a security boundary
- `color="red"` + `line_style="dashed"` → Convention for exposed zones
- `components_inside=["WAF"]` → Boundary has protection mechanism
- **Conclusion:** Public-facing security zone with web application firewall

### Art/Design Agent Interprets:
- `color="red"` + `line_style="dashed"` → Attention-grabbing design element
- `shape="rectangle"` → Structured, organized layout
- **Conclusion:** Hierarchical visual organization with emphasis on this region

### Business Process Agent Interprets:
- `boundary_name="DMZ"` → Probably not a business process phase
- **Conclusion:** Ignore this boundary, focus on swimlanes labeled "Phase 1", "Approval"

## Implementation Checklist

- [ ] Rename `TrustBoundary` model to `VisualBoundary`
- [ ] Remove interpretive fields (`security_level`, `protection_mechanisms`, etc.)
- [ ] Add visual detail fields to `VisualComponent` (colors, decorations, borders)
- [ ] Add visual detail fields to `VisualConnection` (colors, thickness, decorations)
- [ ] Rename tool `detect_trust_boundaries` → `extract_boundaries`
- [ ] Update prompts to remove all domain interpretation
- [ ] Remove 7 non-extraction tools
- [ ] Test with architecture diagrams
- [ ] Verify CyberSec agent still works (it should interpret the visual facts)
