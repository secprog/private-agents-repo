from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, confloat, ConfigDict

# Pydantic models for Visual Analysis
class Position(BaseModel):
    x: float
    y: float
    width: float
    height: float


class VisualComponent(BaseModel):
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
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for component identification (0.0-1.0)"
    )


class VisualConnection(BaseModel):
    source: str
    target: str
    connection_type: Literal[
        "arrow", "line", "dotted", "dashed", "thick", "bidirectional", "other"
    ]
    direction: Literal["unidirectional", "bidirectional", "unknown"]
    labels: List[str]
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for connection identification (0.0-1.0)"
    )


class VisualZone(BaseModel):
    name: str
    boundary_type: Literal[
        "dashed_line", "box", "color", "border", "background", "other"
    ]
    components: List[str]


class TextExtraction(BaseModel):
    text: str
    position: Position
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for text extraction (0.0-1.0)"
    )
    text_type: Literal["label", "annotation", "note", "title", "metadata", "other"]


class TechnologyDetection(BaseModel):
    technology_name: str
    category: Literal[
        "cloud_service", "database", "framework", "protocol",
        "tool", "language", "platform", "other"
    ]
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for technology detection (0.0-1.0)"
    )
    indicators: List[str] = Field(
        ..., description="What in the image suggests this technology (logos, text, icons, etc.)"
    )


class DiagramClassification(BaseModel):
    diagram_type: Literal[
        "architecture", "network", "sequence", "flow", "uml",
        "er", "deployment", "component", "infrastructure", "other"
    ]
    notation_standard: Literal["c4", "uml", "archimate", "bpmn", "custom", "unknown"]
    style: str = Field(..., description="Description of diagram style (e.g., 'AWS style', 'hand-drawn', 'formal')")
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for classification (0.0-1.0)"
    )


class ValidationIssue(BaseModel):
    issue_type: Literal[
        "missing_component", "orphan_connection", "duplicate_component",
        "inconsistent_naming", "missing_connection", "invalid_reference", "other"
    ]
    severity: Literal["error", "warning", "info"]
    description: str
    affected_elements: List[str] = Field(default_factory=list)


class CorrectionSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., description="Short description of the correction")
    action: str = Field(..., description="Specific fix or change to apply")
    affected_elements: List[str] = Field(
        default_factory=list,
        description="Components or connections impacted by this correction"
    )
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="Urgency/impact of applying the correction"
    )
    impact: str = Field(
        default="", description="Expected improvement after applying the correction"
    )


class ValidationResult(BaseModel):
    is_valid: bool
    issues: List[ValidationIssue]
    corrections: List[CorrectionSuggestion] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    quality_score: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Overall quality score (0.0-1.0)"
    )


class InferredRelationship(BaseModel):
    source: str
    target: str
    relationship_type: Literal[
        "depends_on", "uses", "contains", "communicates_with",
        "transforms", "stores", "monitors", "other"
    ]
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for inferred relationship (0.0-1.0)"
    )
    reasoning: str = Field(..., description="Why this relationship was inferred")


class LayoutGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_name: str = Field(..., description="Name or label for the visual group")
    group_type: Literal[
        "layer", "zone", "cluster", "swimlane", "boundary", "other"
    ] = Field(..., description="Kind of grouping represented")
    description: str = Field(
        default="", description="Summary of what the group represents"
    )
    components: List[str] = Field(
        default_factory=list,
        description="Components contained within this group",
    )
    position: Optional[Position] = Field(
        default=None,
        description="Bounding box describing the group's visual region if available",
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(
        default=0.0, description="Confidence score for the group identification"
    )


class LayoutStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout_type: Literal[
        "hierarchical", "layered", "circular", "grid", "freeform", "other"
    ]
    layers: List[str] = Field(default_factory=list, description="Identified layers/tiers")
    groups: List[LayoutGroup] = Field(
        default_factory=list, description="Visual groups identified"
    )
    hierarchy_levels: int = Field(default=0, description="Number of hierarchy levels detected")


class StylingPattern(BaseModel):
    pattern_type: Literal[
        "color_coding", "shape_coding", "line_style", "size_coding", "other"
    ]
    description: str
    elements: List[str] = Field(default_factory=list, description="Elements using this pattern")
    meaning: str = Field(default="", description="Interpreted meaning of the pattern")


class Annotation(BaseModel):
    text: str
    position: Position
    annotation_type: Literal[
        "note", "warning", "callout", "comment", "label", "other"
    ]
    associated_element: str = Field(default="", description="Component/connection this annotation refers to")
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for annotation extraction (0.0-1.0)"
    )


class DiagramComparison(BaseModel):
    added_elements: List[Dict[str, Any]] = Field(default_factory=list)
    removed_elements: List[Dict[str, Any]] = Field(default_factory=list)
    modified_elements: List[Dict[str, Any]] = Field(default_factory=list)
    unchanged_elements: List[Dict[str, Any]] = Field(default_factory=list)
    similarity_score: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Overall similarity score (0.0-1.0)"
    )


class EnhancedAnalysis(BaseModel):
    original_analysis: Dict[str, Any]
    improvements: List[Dict[str, Any]] = Field(default_factory=list)
    new_detections: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_improvements: Dict[str, float] = Field(default_factory=dict)
    quality_score: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Improved quality score (0.0-1.0)"
    )


# Models for OCR and text extraction
class OCRTextResult(BaseModel):
    text: str
    position: Position
    confidence: confloat(ge=0.0, le=1.0)
    source: Literal["paddleocr", "gpt4o", "consensus"]


class ConsensusTextResult(BaseModel):
    texts: List[OCRTextResult]
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    overall_confidence: confloat(ge=0.0, le=1.0)


# Models for export tools
class PlantUMLExport(BaseModel):
    plantuml_code: str
    description: str
    diagram_type: Literal["component", "deployment", "class", "sequence", "usecase", "activity", "state"]


class MermaidExport(BaseModel):
    mermaid_code: str
    description: str
    diagram_type: Literal["flowchart", "sequence", "class", "state", "er", "journey", "gantt", "pie", "graph"]


class DrawIOExport(BaseModel):
    drawio_xml: str
    description: str
    diagram_type: Literal["architecture", "network", "flowchart", "infrastructure", "component", "other"]
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the diagram")


# Models for advanced vision analysis
class LegendMapping(BaseModel):
    symbol_type: Literal["color", "shape", "line_style", "icon", "pattern", "other"]
    symbol_value: str = Field(..., description="Visual representation (e.g., 'red', 'dashed', 'cylinder')")
    meaning: str = Field(..., description="What this symbol represents")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence in mapping")


class LegendExtraction(BaseModel):
    legend_title: str = Field(default="", description="Legend box title if present")
    mappings: List[LegendMapping]
    position: Optional[Position] = None


class LineCrossing(BaseModel):
    line1_id: str = Field(..., description="Identifier for first line/connection")
    line2_id: str = Field(..., description="Identifier for second line/connection")
    intersection_point: Position
    is_actual_intersection: bool = Field(
        ..., description="True if lines actually connect, False if just visual crossing"
    )
    has_bridge_symbol: bool = Field(
        default=False, description="Whether there's a bridge/tunnel symbol at crossing"
    )
    confidence: confloat(ge=0.0, le=1.0)


class TrustBoundary(BaseModel):
    boundary_name: str
    boundary_type: Literal[
        "internet_facing", "dmz", "internal_network", "private_subnet",
        "public_subnet", "security_zone", "trust_zone", "other"
    ]
    position: Position
    components_inside: List[str] = Field(
        default_factory=list, description="Components within this boundary"
    )
    security_level: Literal["public", "restricted", "confidential", "highly_confidential"] = Field(
        default="restricted", description="Security classification"
    )
    protection_mechanisms: List[str] = Field(
        default_factory=list, description="Firewalls, WAF, etc. protecting this boundary"
    )
    confidence: confloat(ge=0.0, le=1.0)


# Models for image preprocessing
class ImageQualityAssessment(BaseModel):
    overall_quality: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Overall image quality score (0.0-1.0)"
    )
    resolution: str = Field(..., description="Image resolution (e.g., '1920x1080')")
    clarity: confloat(ge=0.0, le=1.0) = Field(..., description="Clarity score")
    brightness: confloat(ge=0.0, le=1.0) = Field(..., description="Brightness adequacy")
    contrast: confloat(ge=0.0, le=1.0) = Field(..., description="Contrast adequacy")
    issues: List[str] = Field(default_factory=list, description="Quality issues detected")
    recommendations: List[str] = Field(default_factory=list)


class PreprocessingResult(BaseModel):
    original_filename: str
    processed_filename: str
    operations_applied: List[str]
    quality_improvement: float = Field(..., description="Quality score improvement")


# Models for region-based analysis
class ImageRegion(BaseModel):
    region_id: str
    position: Position
    region_type: Literal["header", "body", "footer", "zone", "layer", "group"]
    description: str
    complexity_score: confloat(ge=0.0, le=1.0)


class RegionalAnalysis(BaseModel):
    region: ImageRegion
    components: List[VisualComponent] = Field(default_factory=list)
    connections: List[VisualConnection] = Field(default_factory=list)
    zones: List[VisualZone] = Field(default_factory=list)
    quality_score: confloat(ge=0.0, le=1.0)


class ComprehensiveRegionalAnalysis(BaseModel):
    regions: List[RegionalAnalysis]
    merged_components: List[VisualComponent]
    merged_connections: List[VisualConnection]
    merged_zones: List[VisualZone]
    overall_quality: confloat(ge=0.0, le=1.0)


# Model for iterative refinement
class IterativeAnalysisResult(BaseModel):
    final_analysis: Dict[str, Any]
    iterations_completed: int
    quality_progression: List[float] = Field(
        default_factory=list, description="Quality score at each iteration"
    )
    improvements_made: List[str] = Field(default_factory=list)
    final_quality_score: confloat(ge=0.0, le=1.0)

