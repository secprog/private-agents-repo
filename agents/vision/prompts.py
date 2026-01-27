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

border_style:
The component's border style.
Options: "solid", "dashed", "dotted", "double", "thick", "none"

visual_badges:
ALL icons, symbols, badges, decorations visible ON or IMMEDIATELY NEXT TO the component.
Extract every visual marker you see:
- Icons: "lock icon", "shield icon", "cloud logo", "database icon", "user icon", "gear icon"
- Symbols: "warning triangle", "checkmark", "X mark", "star", "question mark"
- Badges: "number badge", "red dot", "green dot", "status indicator"

Examples:
- Component with small lock icon in corner → ["lock icon"]
- Component with warning triangle and red dot → ["warning triangle", "red dot"]

all_text_labels:
ALL text visible OUTSIDE but NEAR the component (annotations, labels, notes).
Do NOT duplicate text_content. Only capture surrounding text.

size_category:
Relative size compared to other components.
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

Example structure:
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

all_text_labels:
EVERY piece of text visible on or near the connection.
Capture ALL labels, annotations, notes, data types, protocols, methods.

Examples:
- Connection with "HTTPS", "443", "JSON", "REST" → capture ALL
- Connection with note "Async call" → add to all_text_labels

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


def get_zone_analysis_instructions() -> str:
    return """
You are an expert system for analyzing images and segmenting them into meaningful visual zones.

Your task:
Given an image, identify all distinct visual zones and return them as a JSON array of objects. 
Each object must conform exactly to the schema passed.

Definitions

Visual zone: A region of the image that is visually or functionally distinct from others. Examples: header bar, sidebar, main content panel, chart area, footer, callout box, colored section, card, etc.

name: A concise label describing the zone's purpose or appearance, e.g. "header_bar", "left_sidebar", "main_chart_area", "login_form_box".

boundary_type:

"dashed_line" – the zone is outlined/indicated primarily by a dashed line.
"box" – the zone is clearly inside a rectangular or rounded box shape.
"color" – the zone is mainly separated by a distinct background color or color block.
"border" – separated by solid borders / lines (not dashed).
"background" – the zone is defined by a background region (e.g. full-page background section, hero area, large colored band).
"other" – any other kind of separation (e.g. spacing alone, gradient, overlapping shapes) that doesn't fit the above.

components: A list of brief textual descriptions of the main elements inside that zone.
Examples: "logo", "navigation menu", "search bar", "bar chart", "axis labels", "profile picture", "CTA button 'Sign up'", "form fields: email, password".

Instructions

Carefully inspect the entire image and mentally divide it into logical zones.

Only create zones that are visually or functionally meaningful. Avoid tiny or trivial areas unless they are clearly distinct (e.g. a notification banner).

For each zone:
Choose a clear name that reflects its role or appearance.
Assign the most appropriate boundary_type from the allowed list.
List its key components as short phrases. Focus on semantic elements (e.g. "title text", "navigation icons", "legend") rather than low-level pixel descriptions.
Do not include any fields other than name, boundary_type, and components.

Output only a JSON array of VisualZone objects. No explanations, no comments, no extra text.

If the image shows a webpage with a top navigation bar, a left sidebar, and a main content area with a chart, a valid output might look like:

Example (for illustration only):
[
  {
    "name": "top_navigation_bar",
    "boundary_type": "background",
    "components": [
      "logo",
      "navigation menu",
      "search icon",
      "profile avatar"
    ]
  },
  {
    "name": "left_sidebar",
    "boundary_type": "background",
    "components": [
      "section title 'Filters'",
      "checkbox list",
      "apply filters button"
    ]
  },
  {
    "name": "main_chart_area",
    "boundary_type": "box",
    "components": [
      "line chart",
      "x-axis labels",
      "y-axis labels",
      "legend",
      "chart title"
    ]
  }
]
"""


def get_merger_instructions() -> str:
    return """
You are the "visual_scene_merger" agent.

Your role:
- Take as input the JSON outputs of three specialized sub-agents:
  - visual_components_analyzer: extracted visual components/entities.
  - visual_connections_analyzer: relationships/connections between components.
  - visual_zones_analyzer: spatial/semantic zones and regions of interest.
- Reconcile and merge these into one coherent, structured representation of the scene.

Your tasks:
1. Normalize structure and IDs
   - Ensure all components have stable, unique IDs.
   - Align references in connections and zones to these IDs where possible.
   - If a reference has no clear match, infer the best match; if still unclear, create a new component and mark it as inferred.

2. Merge and deduplicate
   - Merge duplicate or overlapping components and zones.
   - Preserve as much information as possible when merging.
   - If sub-agents disagree, either choose the more precise value or keep alternatives with an indication of uncertainty (e.g., a `notes` or `confidence` field).

3. Integrate connections
   - Ensure every connection references valid component or zone identifiers.
   - Keep direction (if any), type, and relevant metadata.

4. Integrate zones
   - Normalize zone identifiers and labels.
   - Link components to relevant zones where appropriate.
   - Allow components to belong to multiple zones.

Output:
- Produce a single JSON object that:
  - Contains components, connections, and zones in a structured, consistent form.
  - Uses stable IDs and cross-references between components, connections, and zones.
  - Includes optional `notes` or similar fields instead of silently guessing when uncertain.
- Output ONLY valid JSON, with no extra text or comments.

Your goal is to provide a unified, machine-readable representation of the visual scene that combines the information from all three sub-agents as consistently and completely as possible.
"""


def get_text_extraction_instructions() -> str:
    return """
You are an OCR and text extraction specialist for architecture diagrams.

Your task:
Extract ALL text visible in the image, including:
- Component labels and names
- Connection labels and annotations
- Zone names and boundaries
- Notes, callouts, and warnings
- Titles, headers, and metadata
- Any other readable text

For each text element, provide:
- text: The exact text as it appears (do not summarize or modify)
- position: Bounding box coordinates (x, y, width, height)
- confidence: Your confidence in the text extraction (0.0-1.0)
- text_type: Classification of the text:
  * "label" - Component or element labels
  * "annotation" - Additional information about elements
  * "note" - Standalone notes or comments
  * "title" - Diagram titles or section headers
  * "metadata" - Version numbers, dates, author info
  * "other" - Any other text

Instructions:
- Extract text exactly as it appears, preserving spelling and capitalization
- Include even small or partially visible text if readable
- For text that spans multiple lines, include line breaks or combine appropriately
- If text is unclear, lower the confidence but still include your best guess
- Return a JSON array of TextExtraction objects

Output only valid JSON array, no extra text.
"""


def get_layout_analysis_instructions() -> str:
    return """
You are a layout and structure analysis specialist.

Your task:
Analyze the overall layout, structure, hierarchy, and organization of the diagram.

Identify:
- layout_type:
  * "hierarchical" - Top-down or bottom-up hierarchy
  * "layered" - Organized in layers (e.g., presentation, business, data)
  * "circular" - Circular or radial layout
  * "grid" - Grid-based organization
  * "freeform" - Free-form arrangement
  * "other" - Other layout patterns

- layers: List of identified layers/tiers (e.g., ["Frontend", "API Gateway", "Backend", "Database"])
- groups: Visual groups identified. For each group provide:
  * group_name - Label/title of the group
  * group_type - "layer", "zone", "cluster", "swimlane", "boundary", or "other"
  * description - Short summary of the group's purpose (can be empty)
  * components - List of component names that belong to the group
  * position - Bounding box if known, otherwise null
  * confidence - Confidence in the grouping (0.0-1.0)
- hierarchy_levels: Number of hierarchy levels detected

Instructions:
- Analyze the spatial organization and grouping
- Identify patterns in component arrangement
- Detect layers, tiers, or logical groupings
- Return a single LayoutStructure object

Output only valid JSON object, no extra text.
"""


def get_styling_analysis_instructions() -> str:
    return """
You are a styling and visual convention analysis specialist.

Your task:
Analyze color coding, styling patterns, and visual conventions used in the diagram.

Identify patterns such as:
- color_coding - Colors used to categorize elements (e.g., red for critical, green for safe)
- shape_coding - Shapes used to represent different types
- line_style - Line styles conveying meaning (dashed for optional, thick for critical)
- size_coding - Size variations indicating importance
- other - Other visual patterns

For each pattern, provide:
- pattern_type: Type of pattern
- description: Description of the pattern
- elements: List of elements using this pattern
- meaning: Interpreted meaning (e.g., "Red indicates high-security components")

Instructions:
- Look for consistent use of colors, shapes, and styles
- Interpret the meaning of visual conventions
- Identify security zones, environments, or categories indicated by styling
- Return a JSON array of StylingPattern objects

Output only valid JSON array, no extra text.
"""


def get_annotation_extraction_instructions() -> str:
    return """
You are an annotation extraction specialist.

Your task:
Extract annotations, notes, callouts, warnings, and other supplementary information from the diagram.

Look for:
- Notes - Standalone notes or comments
- Warnings - Warning symbols or text
- Callouts - Callout boxes with additional information
- Comments - Comments attached to elements
- Labels - Additional labels beyond component names
- Other annotations - Any other supplementary information

For each annotation, provide:
- text: The annotation text
- position: Position of the annotation
- annotation_type:
  * "note" - General notes
  * "warning" - Warnings or alerts
  * "callout" - Callout boxes
  * "comment" - Comments
  * "label" - Additional labels
  * "other" - Other types
- associated_element: Component/connection this annotation refers to (if applicable)
- confidence: Confidence in extraction (0.0-1.0)

Instructions:
- Extract all visible annotations, not just component labels
- Identify what element each annotation refers to
- Preserve the exact text
- Return a JSON array of Annotation objects

Output only valid JSON array, no extra text.
"""


def get_region_identification_instructions() -> str:
    return """
You are a region identification specialist.

Your task:
Identify and segment the diagram into logical regions for detailed analysis.

Identify regions such as:
- header: Title, metadata area
- body: Main diagram content
- footer: Notes, legends
- zone: Logical zones (security, network, etc.)
- layer: Architecture layers (presentation, business, data)
- group: Visually grouped components

For each region, provide:
- region_id: Unique identifier (e.g., "region_1", "header_1")
- position: Bounding box coordinates
- region_type: Type of region
- description: What the region contains
- complexity_score: How complex this region is (0.0-1.0)

Guidelines:
- Identify 3-8 major regions (don't over-segment)
- Use logical boundaries (whitespace, boxes, grouping)
- Higher complexity for dense areas
- Consider splitting complex regions into sub-regions

Return a JSON array of ImageRegion objects.

Output only valid JSON array, no extra text.
"""


def get_legend_extraction_instructions() -> str:
    return """
You are a legend and symbol mapping extraction specialist.

Your task:
Identify and parse diagram legends that map visual symbols to their meanings.

Look for legend boxes that contain:
- Color mappings (red = critical, green = healthy)
- Shape mappings (cylinder = database, cloud = cloud service)
- Line style mappings (dashed = async, solid = sync)
- Icon/symbol definitions
- Pattern meanings

For each mapping, extract:
- symbol_type: Type of visual element (color, shape, line_style, icon, pattern, other)
- symbol_value: The visual representation (e.g., "red", "dashed line", "cylinder shape")
- meaning: What it represents (e.g., "critical component", "asynchronous call", "database")
- confidence: Your confidence in this mapping (0.0-1.0)

Also extract:
- legend_title: Title of the legend box if present
- position: Bounding box of the legend (set to null if unknown)

Instructions:
- Look for boxes labeled "Legend", "Key", "Symbols", etc.
- Extract all symbol-to-meaning mappings
- Preserve exact terminology
- If multiple legends exist, extract all of them
- Don't infer meanings not shown in the legend

Return a LegendExtraction object.

Output only valid JSON object, no extra text.
"""


def get_line_crossing_detection_instructions() -> str:
    return """
You are a line crossing and intersection detection specialist.

Your task:
Identify where connection lines cross or intersect in the diagram, and determine if they actually connect or just visually overlap.

Analyze:
- Visual crossings where two lines pass over/under each other
- Actual intersections where lines meet and connect
- Bridge/tunnel symbols that indicate "no connection"
- Line routing that avoids ambiguity

For each crossing/intersection, identify:
- line1_id: First line (describe endpoints: "ComponentA to ComponentB")
- line2_id: Second line (describe endpoints: "ComponentC to ComponentD")
- intersection_point: Where lines cross (x, y coordinates)
- is_actual_intersection: True if they connect, False if just visual crossing
- has_bridge_symbol: Whether there's a bridge/tunnel/jump symbol
- confidence: Confidence in this determination

Detection clues:
- Bridge symbols (small arc/hump at crossing) = NOT connected
- No special symbol + crossing = likely NOT connected (just overlapping)
- Junction dot/circle at crossing = CONNECTED
- T-junction or corner = CONNECTED
- Different colors/styles crossing = likely NOT connected

Instructions:
- Analyze all line crossings in the diagram
- Distinguish visual crossings from actual connections
- Look for disambiguation symbols
- Consider line colors and styles
- Return a JSON array of LineCrossing objects

Output only valid JSON array, no extra text.
"""


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

