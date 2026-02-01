from typing import Annotated, List, Literal, Optional

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
        "icon", "labeled_box", "container", "shape",
        "image", "text_block", "badge", "indicator", "actor", "other"
    ] = Field(..., description="Visual category of the component as it appears in the diagram")
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
    visual_observation: str = Field(..., description="What this pattern looks like visually (e.g., 'all red boxes are grouped together', 'dashed lines connect to elements outside the boundary')")


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


class ImageRegion(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    region_id: str
    position: Position
    region_type: Literal["header", "body", "footer", "zone", "layer", "group"]
    description: str
    complexity_score: Annotated[float, Field(ge=0.0, le=1.0)]
