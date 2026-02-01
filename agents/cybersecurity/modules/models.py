from typing import Annotated, List, Literal

from pydantic import BaseModel, Field


# Security Context - first pass interpretation of generic visual data
class IdentifiedComponent(BaseModel):
    """A visual component interpreted for its IT/security role"""
    visual_name: str = Field(..., description="Original component name from vision data")
    inferred_role: Literal[
        "database", "application", "gateway", "cloud_service", "load_balancer",
        "firewall", "waf", "proxy", "cache", "queue", "storage", "compute",
        "network", "monitoring", "cdn", "dns", "identity_provider",
        "container_orchestrator", "serverless", "api", "frontend", "backend",
        "message_broker", "secret_manager", "logging", "user", "external_service", "other"
    ] = Field(..., description="Inferred IT role based on text_content, all_text_labels, visual_badges, visual_type")
    technology: str = Field(..., description="Identified technology (e.g., 'PostgreSQL 14', 'AWS Lambda', 'Nginx')")
    exposure_level: Literal["internet_facing", "dmz", "internal", "isolated", "unknown"] = Field(..., description="Inferred exposure level")
    security_controls_present: List[str] = Field(..., description="Security controls identified from visual badges/labels (e.g., 'encryption', 'authentication', 'WAF')")
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Confidence in interpretation")]


class IdentifiedConnection(BaseModel):
    """A visual connection interpreted for its security properties"""
    source: str = Field(..., description="Source component name")
    target: str = Field(..., description="Target component name")
    inferred_protocol: str = Field(..., description="Inferred protocol from labels (e.g., 'HTTPS', 'gRPC', 'SQL', 'unknown')")
    encryption_status: Literal["encrypted", "unencrypted", "unknown"] = Field(..., description="Inferred encryption status")
    crosses_trust_boundary: bool = Field(..., description="Whether this connection crosses a security zone boundary")
    security_concerns: List[str] = Field(..., description="Any security concerns about this connection")
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Confidence in interpretation")


class IdentifiedSecurityZone(BaseModel):
    """A visual boundary interpreted as a security zone"""
    boundary_name: str = Field(..., description="Original boundary name from vision data")
    inferred_zone_type: Literal[
        "internet", "dmz", "public_subnet", "private_subnet", "vpc",
        "internal_network", "management_zone", "data_zone", "isolated_segment", "other"
    ] = Field(..., description="Inferred security zone type from text_labels, colors, styles")
    security_level: Literal["critical", "high", "medium", "low"] = Field(..., description="Inferred security level")
    components_inside: List[str] = Field(..., description="Components within this zone")
    boundary_controls: List[str] = Field(..., description="Security controls at the boundary (inferred from visual data)")
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Confidence in interpretation")


class SecurityContext(BaseModel):
    """First-pass interpretation of generic visual data into security context"""
    components: List[IdentifiedComponent] = Field(..., description="Components with inferred IT roles and technologies")
    connections: List[IdentifiedConnection] = Field(..., description="Connections with inferred protocols and encryption")
    security_zones: List[IdentifiedSecurityZone] = Field(..., description="Boundaries interpreted as security zones")
    diagram_type: str = Field(..., description="Inferred diagram type (e.g., 'cloud architecture', 'network topology', 'microservices', 'data flow')")
    overall_notes: List[str] = Field(..., description="General observations about the architecture's security posture")
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Overall confidence in security context interpretation")]


# Detailed Security Analysis Models
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
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Confidence in threat identification")]


class VulnerabilityAssessment(BaseModel):
    vulnerability_id: str = Field(..., description="Unique identifier for the vulnerability")
    component_name: str = Field(..., description="Affected component name")
    technology: str = Field(..., description="Technology/service with vulnerability")
    vulnerability_type: Literal[
        "outdated_version", "missing_encryption", "weak_authentication",
        "insecure_configuration", "missing_security_control", "exposed_service",
        "insufficient_logging", "lack_of_segmentation", "other"
    ] = Field(..., description="Type of vulnerability")
    cvss_score: Annotated[float, Field(ge=0.0, le=10.0, description="CVSS score if applicable")]
    description: str = Field(..., description="Description of the vulnerability")
    remediation: str = Field(..., description="Recommended remediation steps")
    priority: Literal["critical", "high", "medium", "low"] = Field(..., description="Remediation priority")
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Confidence in assessment")]


class AttackPath(BaseModel):
    path_id: str = Field(..., description="Unique identifier for the attack path")
    path_name: str = Field(..., description="Name of the attack path")
    entry_point: str = Field(..., description="Initial entry point component")
    target: str = Field(..., description="Final target component")
    intermediate_components: List[str] = Field(..., description="Components traversed")
    steps: List[str] = Field(..., description="Step-by-step attack progression")
    risk_level: Literal["critical", "high", "medium", "low"] = Field(..., description="Overall risk level")
    mitigation: str = Field(..., description="How to mitigate this attack path")
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Confidence in path analysis")]


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
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(..., description="Confidence in assessment")


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
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Confidence in recommendation")]


class SecurityPosture(BaseModel):
    overall_score: Annotated[float, Field(ge=0.0, le=100.0, description="Overall security score (0-100)")]
    maturity_level: Literal["initial", "developing", "defined", "managed", "optimizing"] = Field(..., description="Security maturity level")
    strengths: List[str] = Field(..., description="Identified security strengths")
    weaknesses: List[str] = Field(..., description="Identified security weaknesses")
    critical_gaps: List[str] = Field(..., description="Critical security gaps")
    quick_wins: List[str] = Field(..., description="Easy improvements with high impact")


# Phase output wrapper models (for LLM output schema enforcement)
class ThreatAnalysisResult(BaseModel):
    """Output of Phase 2: threat and vulnerability analysis"""
    threats: List[ThreatIdentification] = Field(..., description="Identified threats")
    vulnerabilities: List[VulnerabilityAssessment] = Field(..., description="Vulnerability assessments")


class AttackPathResult(BaseModel):
    """Output of Phase 3: attack path analysis"""
    attack_paths: List[AttackPath] = Field(..., description="Potential attack paths")


class ComplianceResult(BaseModel):
    """Output of Phase 4: compliance assessment"""
    compliance_checks: List[ComplianceCheck] = Field(..., description="Compliance assessments")


class RecommendationsResult(BaseModel):
    """Output of Phase 5: recommendations and posture"""
    security_posture: SecurityPosture = Field(..., description="Overall security posture assessment")
    recommendations: List[SecurityRecommendation] = Field(..., description="Security recommendations")
    analysis_summary: str = Field(..., description="Executive summary of findings")
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Overall confidence in analysis")]
