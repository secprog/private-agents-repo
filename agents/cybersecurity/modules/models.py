from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, confloat

# Pydantic models for Visual Analysis
class Position(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

    x: float
    y: float


class VisualComponent(BaseModel):
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

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
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})

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


# NEW: Comprehensive Security Analysis Models
class ThreatIdentification(BaseModel):
    threat_id: str = Field(..., description="Unique identifier for the threat")
    threat_name: str = Field(..., description="Name of the threat (e.g., 'Unauthorized Database Access')")
    threat_category: Literal[
        "data_breach", "unauthorized_access", "injection_attack", "dos_ddos",
        "mitm", "privilege_escalation", "lateral_movement", "data_exfiltration",
        "misconfiguration", "credential_theft", "supply_chain", "other"
    ] = Field(..., description="Category of the threat")
    affected_components: List[str] = Field(..., description="List of component names affected")
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(..., description="Severity level")
    likelihood: Literal["very_high", "high", "medium", "low", "very_low"] = Field(..., description="Likelihood of exploitation")
    description: str = Field(..., description="Detailed description of the threat")
    attack_vector: str = Field(..., description="How the attack could be carried out")
    impact: str = Field(..., description="Potential impact if exploited")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence in threat identification")


class VulnerabilityAssessment(BaseModel):
    vulnerability_id: str = Field(..., description="Unique identifier for the vulnerability")
    component_name: str = Field(..., description="Affected component name")
    technology: str = Field(..., description="Technology/service with vulnerability")
    vulnerability_type: Literal[
        "outdated_version", "missing_encryption", "weak_authentication",
        "insecure_configuration", "missing_security_control", "exposed_service",
        "insufficient_logging", "lack_of_segmentation", "other"
    ] = Field(..., description="Type of vulnerability")
    cvss_score: confloat(ge=0.0, le=10.0) = Field(..., description="CVSS score if applicable")
    description: str = Field(..., description="Description of the vulnerability")
    remediation: str = Field(..., description="Recommended remediation steps")
    priority: Literal["critical", "high", "medium", "low"] = Field(..., description="Remediation priority")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence in assessment")


class AttackPath(BaseModel):
    path_id: str = Field(..., description="Unique identifier for the attack path")
    path_name: str = Field(..., description="Name of the attack path")
    entry_point: str = Field(..., description="Initial entry point component")
    target: str = Field(..., description="Final target component")
    intermediate_components: List[str] = Field(..., description="Components traversed")
    steps: List[str] = Field(..., description="Step-by-step attack progression")
    risk_level: Literal["critical", "high", "medium", "low"] = Field(..., description="Overall risk level")
    mitigation: str = Field(..., description="How to mitigate this attack path")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence in path analysis")


class ComplianceCheck(BaseModel):
    framework: Literal[
        "GDPR", "HIPAA", "PCI_DSS", "SOC2", "ISO27001", "NIST",
        "CIS", "OWASP", "FedRAMP", "general"
    ] = Field(..., description="Compliance framework")
    requirement_id: str = Field(..., description="Specific requirement ID")
    requirement_name: str = Field(..., description="Name of the requirement")
    status: Literal["compliant", "non_compliant", "partial", "not_applicable"] = Field(..., description="Compliance status")
    affected_components: List[str] = Field(..., description="Components related to this requirement")
    finding: str = Field(..., description="Detailed finding")
    recommendation: str = Field(..., description="Recommendation for compliance")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence in assessment")


class SecurityRecommendation(BaseModel):
    recommendation_id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Short title of the recommendation")
    category: Literal[
        "network_security", "access_control", "encryption", "monitoring",
        "architecture", "configuration", "patch_management", "incident_response",
        "data_protection", "identity_management", "other"
    ] = Field(..., description="Category of recommendation")
    priority: Literal["critical", "high", "medium", "low"] = Field(..., description="Implementation priority")
    affected_components: List[str] = Field(..., description="Components affected")
    description: str = Field(..., description="Detailed description")
    implementation_steps: List[str] = Field(..., description="Steps to implement")
    estimated_effort: Literal["low", "medium", "high", "very_high"] = Field(..., description="Implementation effort")
    expected_impact: str = Field(..., description="Expected security improvement")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence in recommendation")


class SecurityPosture(BaseModel):
    overall_score: confloat(ge=0.0, le=100.0) = Field(..., description="Overall security score (0-100)")
    maturity_level: Literal["initial", "developing", "defined", "managed", "optimizing"] = Field(..., description="Security maturity level")
    strengths: List[str] = Field(..., description="Identified security strengths")
    weaknesses: List[str] = Field(..., description="Identified security weaknesses")
    critical_gaps: List[str] = Field(..., description="Critical security gaps")
    quick_wins: List[str] = Field(..., description="Easy improvements with high impact")


class ComprehensiveSecurityAnalysis(BaseModel):
    """Complete security analysis leveraging all vision data"""
    # Summary
    security_posture: SecurityPosture = Field(..., description="Overall security posture assessment")

    # Detailed Analysis
    threats: List[ThreatIdentification] = Field(..., description="Identified threats")
    vulnerabilities: List[VulnerabilityAssessment] = Field(..., description="Vulnerability assessments")
    attack_paths: List[AttackPath] = Field(..., description="Potential attack paths")

    # Compliance & Recommendations
    compliance_checks: List[ComplianceCheck] = Field(..., description="Compliance assessments")
    recommendations: List[SecurityRecommendation] = Field(..., description="Security recommendations")

    # Metadata
    analysis_summary: str = Field(..., description="Executive summary of findings")
    confidence: confloat(ge=0.0, le=1.0) = Field(..., description="Overall confidence in analysis")