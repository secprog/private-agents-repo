from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

# Pydantic models for Visual Analysis
class Position(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    x: float
    y: float
    width: float
    height: float


class VisualComponent(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    name: str
    component_type: Literal[
        "application", "service", "database", "cache", "queue",
        "api_gateway", "load_balancer", "storage", "network",
        "security", "monitoring", "user", "external_service", "other"
    ] = Field(..., description="Semantic role/type of the component")
    visual_type: Literal[
        "box", "circle", "icon", "diamond", "cylinder", "cloud", "other"
    ]
    position: Position
    text_content: str
    visual_group: str
    primary_color: str = Field(
        ...,
        description="Main color of the component (red, blue, green, orange, gray, black, etc.)"
    )
    border_style: str = Field(
        ...,
        description="Border style: solid, dashed, dotted, double, thick, none"
    )
    visual_badges: List[str] = Field(
        ...,
        description="Visual icons, symbols, badges visible on or near component"
    )
    all_text_labels: List[str] = Field(
        ...,
        description="ALL text visible on or near this component"
    )
    size_category: Literal["very_small", "small", "medium", "large", "very_large"] = Field(
        ...,
        description="Relative size compared to other components"
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for component identification (0.0-1.0)"
    )


class VisualConnection(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    source: str
    target: str
    connection_type: Literal[
        "arrow", "line", "dotted", "dashed", "thick", "bidirectional", "other"
    ]
    direction: Literal["unidirectional", "bidirectional", "unknown"]
    labels: List[str]
    color: str = Field(
        ...,
        description="Color of the connection line"
    )
    thickness: Literal["very_thin", "thin", "normal", "thick", "very_thick"] = Field(
        ...,
        description="Visual thickness/weight of the line"
    )
    line_pattern: str = Field(
        ...,
        description="Line pattern: solid, small-dashes, large-dashes, dots, dot-dash"
    )
    visual_markers: List[str] = Field(
        ...,
        description="Icons or symbols ON the connection line"
    )
    all_text_labels: List[str] = Field(
        ...,
        description="ALL text on or near the connection"
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for connection identification (0.0-1.0)"
    )


class VisualZone(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    name: str
    boundary_type: Literal[
        "dashed_line", "box", "color", "border", "background", "other"
    ]
    components: List[str]


class TextExtraction(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    text: str
    position: Position
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for text extraction (0.0-1.0)"
    )
    text_type: Literal["label", "annotation", "note", "title", "metadata", "other"]


class TechnologyDetection(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    technology_name: str
    category: Literal[
        "cloud_service", "database", "framework", "protocol",
        "tool", "language", "platform", "other"
    ]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for technology detection (0.0-1.0)"
    )
    indicators: List[str] = Field(
        ..., description="What in the image suggests this technology (logos, text, icons, etc.)"
    )


class DiagramClassification(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    diagram_type: Literal[
        "architecture", "network", "sequence", "flow", "uml",
        "er", "deployment", "component", "infrastructure", "other"
    ]
    notation_standard: Literal["c4", "uml", "archimate", "bpmn", "custom", "unknown"]
    style: str = Field(..., description="Description of diagram style (e.g., 'AWS style', 'hand-drawn', 'formal')")
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for classification (0.0-1.0)"
    )


class ValidationIssue(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    issue_type: Literal[
        "missing_component", "orphan_connection", "duplicate_component",
        "inconsistent_naming", "missing_connection", "invalid_reference", "other"
    ]
    severity: Literal["error", "warning", "info"]
    description: str
    affected_elements: List[str] = Field(...)


class CorrectionSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    summary: str = Field(..., description="Short description of the correction")
    action: str = Field(..., description="Specific fix or change to apply")
    affected_elements: List[str] = Field(
        ...,
        description="Components or connections impacted by this correction"
    )
    priority: Literal["high", "medium", "low"] = Field(
        ..., description="Urgency/impact of applying the correction"
    )
    impact: str = Field(
        ..., description="Expected improvement after applying the correction"
    )


class ValidationResult(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    is_valid: bool
    issues: List[ValidationIssue]
    corrections: List[CorrectionSuggestion]
    suggestions: List[str]
    quality_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Overall quality score (0.0-1.0)"
    )


class InferredRelationship(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    source: str
    target: str
    relationship_type: Literal[
        "depends_on", "uses", "contains", "communicates_with",
        "transforms", "stores", "monitors", "other"
    ]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for inferred relationship (0.0-1.0)"
    )
    reasoning: str = Field(..., description="Why this relationship was inferred")


class LayoutGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    group_name: str = Field(..., description="Name or label for the visual group")
    group_type: Literal[
        "layer", "zone", "cluster", "swimlane", "boundary", "other"
    ] = Field(..., description="Kind of grouping represented")
    description: str = Field(
        ..., description="Summary of what the group represents"
    )
    components: List[str] = Field(
        ...,
        description="Components contained within this group",
    )
    position: Optional[Position] = Field(
        ...,
        description="Bounding box describing the group's visual region if available",
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for the group identification"
    )


class LayoutStructure(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    layout_type: Literal[
        "hierarchical", "layered", "circular", "grid", "freeform", "other"
    ]
    layers: List[str] = Field(..., description="Identified layers/tiers")
    groups: List[LayoutGroup] = Field(
        ..., description="Visual groups identified"
    )
    hierarchy_levels: int = Field(..., description="Number of hierarchy levels detected")


class StylingPattern(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    pattern_type: Literal[
        "color_coding", "shape_coding", "line_style", "size_coding", "other"
    ]
    description: str
    elements: List[str] = Field(..., description="Elements using this pattern")
    meaning: str = Field(..., description="Interpreted meaning of the pattern")


class Annotation(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    text: str
    position: Position
    annotation_type: Literal[
        "note", "warning", "callout", "comment", "label", "other"
    ]
    associated_element: str = Field(..., description="Component/connection this annotation refers to")
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence score for annotation extraction (0.0-1.0)"
    )


class DiagramComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    added_elements: List["DiagramChangeDetail"]
    removed_elements: List["DiagramChangeDetail"]
    modified_elements: List["DiagramChangeDetail"]
    unchanged_elements: List["DiagramChangeDetail"]
    similarity_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Overall similarity score (0.0-1.0)"
    )


class EnhancedAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_analysis: str = Field(
        ..., description="Original analysis JSON serialized as a string"
    )
    improvements: List["ImprovementDetail"]
    new_detections: List["DetectionDetail"]
    confidence_improvements: List["ConfidenceImprovementEntry"]
    quality_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Improved quality score (0.0-1.0)"
    )


# Models for OCR and text extraction
class OCRTextResult(BaseModel):
    text: str
    position: Position
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    source: Literal["paddleocr", "gpt4o", "consensus"]


class ConsensusTextResult(BaseModel):
    texts: List[OCRTextResult]
    conflicts: List[Dict[str, Any]] = Field(...)
    overall_confidence: Annotated[float, Field(ge=0.0, le=1.0)]


# Models for export tools
class PlantUMLExport(BaseModel):
    plantuml_code: str
    description: str
    diagram_type: Literal["component", "deployment", "class", "sequence", "usecase", "activity", "state"]


class MermaidExport(BaseModel):
    mermaid_code: str
    description: str
    diagram_type: Literal["flowchart", "sequence", "class", "state", "er", "journey", "gantt", "pie", "graph"]


class MetadataEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="Metadata field name")
    value: str = Field(..., description="Metadata value")


class DrawIOExport(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    drawio_xml: str
    description: str
    diagram_type: Literal["architecture", "network", "flowchart", "infrastructure", "component", "other"]
    metadata: List[MetadataEntry] = Field(
        ...,
        description="Additional metadata entries for the diagram",
    )


class DiagramChangeDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    element_name: str = Field(
        ..., description="Identifier or label of the element that changed"
    )
    element_type: Literal["component", "connection", "zone", "other"] = Field(
        ..., description="Type of element that changed"
    )
    description: str = Field(
        ..., description="Summary of what changed for this element"
    )
    attributes: List[MetadataEntry] = Field(
        ...,
        description="Additional structured details about the change",
    )


class ImprovementDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    summary: str = Field(..., description="Short label for the improvement")
    action: str = Field(..., description="Specific fix or change performed")
    affected_elements: List[str] = Field(
        ..., description="Elements impacted by this improvement"
    )
    impact: str = Field(
        ..., description="Expected result or benefit of the improvement"
    )
    attributes: List[MetadataEntry] = Field(
        ...,
        description="Optional structured metadata about the improvement",
    )


class DetectionDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    name: str = Field(..., description="Identifier for the new detection")
    description: str = Field(
        ..., description="Explanation of the detected element"
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Confidence in this detection"
    )
    attributes: List[MetadataEntry] = Field(
        ...,
        description="Optional structured metadata about the detection",
    )


class ConfidenceImprovementEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"additionalProperties": False})

    element_name: str = Field(
        ..., description="Element whose confidence was improved"
    )
    new_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Updated confidence score for the element"
    )


# Models for advanced vision analysis
class LegendMapping(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    symbol_type: Literal["color", "shape", "line_style", "icon", "pattern", "other"]
    symbol_value: str = Field(..., description="Visual representation (e.g., 'red', 'dashed', 'cylinder')")
    meaning: str = Field(..., description="What this symbol represents")
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Confidence in mapping")


class LegendExtraction(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    legend_title: str = Field(..., description="Legend box title if present")
    mappings: List[LegendMapping]
    position: Optional[Position] = Field(...)


class LineCrossing(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    line1_id: str = Field(..., description="Identifier for first line/connection")
    line2_id: str = Field(..., description="Identifier for second line/connection")
    intersection_point: Position
    is_actual_intersection: bool = Field(
        ..., description="True if lines actually connect, False if just visual crossing"
    )
    has_bridge_symbol: bool = Field(
        ..., description="Whether there's a bridge/tunnel symbol at crossing"
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]


class VisualBoundary(BaseModel):
    """Generic visual boundary/enclosure extracted from diagram"""
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    boundary_name: str = Field(
        ...,
        description="Text label on or near the boundary (exact text as shown)"
    )
    visual_style: str = Field(
        ...,
        description="Visual appearance: 'dashed red line', 'thick blue border', 'shaded gray region'"
    )
    color: str = Field(
        ...,
        description="Primary color of the boundary"
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
        ...,
        description="ALL text written on or near this boundary"
    )
    components_inside: List[str] = Field(
        ...,
        description="Names of components visually enclosed by this boundary"
    )
    position: Position
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]


# Models for image preprocessing
class ImageQualityAssessment(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    overall_quality: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ..., description="Overall image quality score (0.0-1.0)"
    )
    resolution: str = Field(..., description="Image resolution (e.g., '1920x1080')")
    clarity: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Clarity score")
    brightness: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Brightness adequacy")
    contrast: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Contrast adequacy")
    issues: List[str] = Field(..., description="Quality issues detected")
    recommendations: List[str] = Field(...)


class PreprocessingResult(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    original_filename: str
    processed_filename: str
    operations_applied: List[str]
    quality_improvement: float = Field(..., description="Quality score improvement")


# Models for region-based analysis
class ImageRegion(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    region_id: str
    position: Position
    region_type: Literal["header", "body", "footer", "zone", "layer", "group"]
    description: str
    complexity_score: Annotated[float, Field(ge=0.0, le=1.0)]


class RegionalAnalysis(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    region: ImageRegion
    components: List[VisualComponent] = Field(...)
    connections: List[VisualConnection] = Field(...)
    zones: List[VisualZone] = Field(...)
    quality_score: Annotated[float, Field(ge=0.0, le=1.0)]


class ComprehensiveRegionalAnalysis(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    regions: List[RegionalAnalysis]
    merged_components: List[VisualComponent]
    merged_connections: List[VisualConnection]
    merged_zones: List[VisualZone]
    overall_quality: Annotated[float, Field(ge=0.0, le=1.0)]


# Model for iterative refinement
class IterativeAnalysisResult(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    final_analysis: Dict[str, Any]
    iterations_completed: int
    quality_progression: List[float] = Field(
        ..., description="Quality score at each iteration"
    )
    improvements_made: List[str] = Field(...)
    final_quality_score: Annotated[float, Field(ge=0.0, le=1.0)]

