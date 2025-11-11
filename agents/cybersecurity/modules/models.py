from typing import List, Literal

from pydantic import BaseModel, Field, confloat

# Pydantic models for Visual Analysis
class Position(BaseModel):
    x: float
    y: float


class VisualComponent(BaseModel):
    name: str
    component_type: Literal[
        "database",
        "application",
        "gateway",
        "cloud_service",
        "load_balancer",
        "firewall",
        "proxy",
        "cache",
        "queue",
        "storage",
        "compute",
        "network",
        "monitoring",
        "other",
    ]
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


class VisualAnalysisResponse(BaseModel):
    visual_components: List[VisualComponent]
    visual_connections: List[VisualConnection]
    visual_zones: List[VisualZone]
    extracted_text: List[str]
    technology_indicators: List[str]


# Pydantic models for Security Analysis
class ComponentSecurity(BaseModel):
    component_name: str
    component_type: Literal[
        "database",
        "application",
        "gateway",
        "cloud_service",
        "load_balancer",
        "firewall",
        "proxy",
        "cache",
        "queue",
        "storage",
        "compute",
        "network",
        "monitoring",
        "other",
    ]
    security_domain: Literal["Internet", "Intranet", "DMZ", "Cloud", "Unknown"]
    technology: str
    exposure_level: Literal["High", "Medium", "Low"]
    security_concerns: List[str]
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Confidence score for security assessment (0.0-1.0)"
    )


class ConnectionSecurity(BaseModel):
    source: str
    target: str
    protocol: str
    security_level: Literal["Secure", "Insecure", "Unknown"]
    encryption: Literal["Encrypted", "Unencrypted", "Unknown"]
    security_concerns: List[str]
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Confidence score for connection security assessment (0.0-1.0)",
    )


class SecurityZone(BaseModel):
    zone_name: str
    security_level: Literal["High", "Medium", "Low"]
    components: List[str]
    boundary_controls: List[str]


class SecurityAnalysisResponse(BaseModel):
    component_security: List[ComponentSecurity]
    connection_security: List[ConnectionSecurity]
    security_zones: List[SecurityZone]
    security_concerns: List[str]
    recommendations: List[str]