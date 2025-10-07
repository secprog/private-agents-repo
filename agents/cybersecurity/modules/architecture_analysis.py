"""
Advanced Architecture Analysis using AI Vision and Multi-modal Processing
"""

import logging
import base64
import json
import io
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from google.adk.agents import Agent
from google.genai.types import Part, Blob

logger = logging.getLogger(__name__)

@dataclass
class Component:
    """Represents a system component"""
    name: str
    type: str  # e.g., "database", "application", "gateway", "service"
    technology: Optional[str] = None  # e.g., "Azure", "AWS", "IBM", "Spring Boot"
    domain: Optional[str] = None  # e.g., "internet", "intranet", "dmz", "unknown"
    description: Optional[str] = None
    position: Optional[Dict[str, float]] = None  # x, y coordinates if available
    confidence: Optional[float] = None  # AI confidence score

@dataclass
class Connection:
    """Represents a connection between components"""
    source: str
    target: str
    protocol: Optional[str] = None  # e.g., "HTTPS", "HTTP", "TCP"
    description: Optional[str] = None
    security_level: Optional[str] = None  # e.g., "secure", "insecure", "encrypted"
    confidence: Optional[float] = None  # AI confidence score

@dataclass
class ArchitectureAnalysis:
    """Complete architecture analysis result"""
    components: List[Component]
    connections: List[Connection]
    technologies: List[str]
    domains: List[str]
    security_concerns: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]

class ArchitectureAnalyzer:
    """Advanced architecture analyzer using AI vision and multi-modal processing"""
    
    def __init__(self, artifact_service=None):        
        # Store the artifact service for loading files
        self.artifact_service = artifact_service
        logger.info(f"🔧 ArchitectureAnalyzer initialized with artifact service: {type(artifact_service)}")
        if hasattr(artifact_service, 'service_type'):
            logger.info(f"🔧 Artifact service type: {artifact_service.service_type}")
        if hasattr(artifact_service, 'artifact_service'):
            logger.info(f"🔧 Underlying artifact service: {type(artifact_service.artifact_service)}")
        
        # Initialize specialized AI agents for different analysis tasks
        self.vision_agent = Agent(
            name="architecture_vision_analyzer",
            description="Specialized AI for visual architecture diagram analysis",
            model="gemini-2.0-flash",  # This model has excellent vision capabilities
            instruction=self._get_vision_analysis_instructions()
        )
        
        self.security_agent = Agent(
            name="security_architecture_analyzer", 
            description="Specialized AI for security analysis of architecture diagrams",
            model="gemini-2.0-flash",
            instruction=self._get_security_analysis_instructions()
        )
    
    def _get_vision_analysis_instructions(self) -> str:
        """Get specialized instructions for visual analysis"""
        return """
You are an expert in analyzing system architecture diagrams through computer vision. Your task is to:

1. **Visual Component Detection**: Identify all visual elements in the diagram including:
   - Boxes, rectangles, circles, and other shapes representing components
   - Text labels and annotations
   - Icons, logos, and visual symbols
   - Arrows, lines, and connection indicators

2. **Spatial Analysis**: Analyze the spatial relationships and layout:
   - Component positioning and grouping
   - Network boundaries and zones (visually separated areas)
   - Data flow directions indicated by arrows
   - Hierarchical relationships

3. **Text Recognition**: Extract all visible text including:
   - Component names and labels
   - Technology names and versions
   - Protocol specifications
   - Domain names and URLs
   - Security annotations

4. **Visual Pattern Recognition**: Identify common architecture patterns:
   - Cloud service icons (Azure, AWS, GCP)
   - Database symbols
   - Network equipment symbols
   - Security boundary indicators
   - Load balancer representations

5. **Context Understanding**: Understand the overall architecture context:
   - System type (web application, microservices, data pipeline, etc.)
   - Technology stack indicators
   - Security model and trust boundaries
   - Data flow patterns

Provide detailed, structured analysis focusing on visual elements and their relationships.
"""
    
    def _get_security_analysis_instructions(self) -> str:
        """Get specialized instructions for security analysis"""
        return """
You are a cybersecurity expert specializing in architecture security analysis. Your task is to:

1. **Security Domain Classification**: Analyze components and classify them into security zones:
   - Internet/Public: External-facing components
   - DMZ: Demilitarized zone components
   - Intranet/Private: Internal corporate network
   - Cloud: Cloud service components
   - Unknown: Unclear or ambiguous security context

2. **Technology Security Assessment**: Evaluate security implications of identified technologies:
   - Cloud platforms (Azure, AWS, GCP) and their security models
   - Database technologies and encryption capabilities
   - API gateways and authentication mechanisms
   - Load balancers and traffic management
   - Container and orchestration security

3. **Data Flow Security Analysis**: Assess security of data flows:
   - Encryption in transit (HTTPS, TLS, etc.)
   - Authentication and authorization mechanisms
   - Data sensitivity and protection requirements
   - Cross-boundary data flows and risks

4. **Vulnerability Identification**: Identify potential security issues:
   - Missing security controls
   - Insecure communication protocols
   - Exposed sensitive components
   - Insufficient network segmentation
   - Authentication/authorization gaps

5. **Compliance and Governance**: Assess compliance considerations:
   - Data protection and privacy requirements
   - Industry standards and regulations
   - Security best practices adherence
   - Risk management and mitigation

Provide actionable security recommendations and risk assessments.
"""
    
    async def analyze_architecture(self, session_id: str, filename: str) -> str:
        """Comprehensive architecture analysis using AI vision and security expertise"""
        try:
            logger.info(f"Starting architecture analysis for session_id={session_id}, filename={filename}")
            
            artifact_data = await self.artifact_service.load_artifact_to_data(filename, session_id)

            if not artifact_data:
                logger.error(f"Could not load artifact: {filename} from session {session_id}")
                raise ValueError(f"Could not load artifact: {filename}")

            logger.info(f"Successfully loaded artifact: {filename} (type: {artifact_data.mime_type})")
            
            # Create Part object for the LLM
            binary_data = base64.b64decode(artifact_data.data)
            part = Part(
                inline_data=Blob(
                    mime_type=artifact_data.mime_type,
                    data=binary_data
                )
            )
            
            # Step 1: Visual Analysis
            visual_analysis = await self._perform_visual_analysis(part, filename)
            
            # Step 2: Security Analysis
            security_analysis = await self._perform_security_analysis(part, visual_analysis)
            
            # Step 3: Combine and structure results
            analysis = self._combine_analyses(visual_analysis, security_analysis, filename, session_id, artifact_data.mime_type)
            
            # Convert to JSON string for ADK compatibility
            return json.dumps({
                'components': [
                    {
                        'name': comp.name,
                        'type': comp.type,
                        'technology': comp.technology,
                        'domain': comp.domain,
                        'description': comp.description,
                        'position': comp.position,
                        'confidence': comp.confidence
                    } for comp in analysis.components
                ],
                'connections': [
                    {
                        'source': conn.source,
                        'target': conn.target,
                        'protocol': conn.protocol,
                        'description': conn.description,
                        'security_level': conn.security_level,
                        'confidence': conn.confidence
                    } for conn in analysis.connections
                ],
                'technologies': analysis.technologies,
                'domains': analysis.domains,
                'security_concerns': analysis.security_concerns,
                'recommendations': analysis.recommendations,
                'metadata': analysis.metadata
            })
            
        except Exception as e:
            logger.error(f"Failed to analyze architecture: {e}")
            raise
    
    
    async def _perform_visual_analysis(self, part: Part, filename: str) -> Dict[str, Any]:
        """Perform detailed visual analysis of the architecture diagram"""
        
        visual_prompt = f"""
Analyze this architecture diagram with advanced computer vision capabilities. 

For the file "{filename}", provide a comprehensive visual analysis including:

1. **Component Detection**: Identify all visual components with:
   - Exact names and labels as they appear
   - Component type (database, application, gateway, cloud_service, load_balancer, etc.) - use your best judgment
   - Visual type (box, circle, icon, etc.)
   - Position coordinates (if determinable)
   - Visual grouping and boundaries

2. **Connection Analysis**: Map all visual connections:
   - Source and target components
   - Connection type (arrow, line, dotted line, etc.)
   - Direction and flow indicators
   - Labels and annotations on connections

3. **Technology Identification**: Identify technologies from visual cues:
   - Cloud service logos and icons
   - Database symbols and representations
   - Technology-specific visual elements
   - Brand colors and styling patterns

4. **Spatial Analysis**: Analyze the layout and organization:
   - Network zones and boundaries (visually separated areas)
   - Hierarchical relationships
   - Data flow patterns
   - Security boundary indicators

5. **Text Extraction**: Extract all visible text including:
   - Component names and descriptions
   - Technology names and versions
   - URLs, domain names, and endpoints
   - Protocol specifications
   - Security annotations

Return your analysis as structured JSON:
{{
    "visual_components": [
        {{
            "name": "exact_name_from_diagram",
            "component_type": "database|application|gateway|cloud_service|load_balancer|etc",
            "visual_type": "box|circle|icon|etc",
            "position": {{"x": 0, "y": 0}},
            "text_content": "all_visible_text",
            "visual_group": "group_identifier"
        }}
    ],
    "visual_connections": [
        {{
            "source": "source_component_name",
            "target": "target_component_name",
            "connection_type": "arrow|line|dotted|etc",
            "direction": "unidirectional|bidirectional",
            "labels": ["connection_labels"]
        }}
    ],
    "visual_zones": [
        {{
            "name": "zone_name",
            "boundary_type": "dashed_line|box|color|etc",
            "components": ["component_names_in_zone"]
        }}
    ],
    "extracted_text": ["all_visible_text_elements"],
    "technology_indicators": ["technology_names_from_visual_cues"]
}}
"""
        
        response = await self.vision_agent.generate_content_async([visual_prompt, part])
        return self._parse_json_response(response.text)
    
    async def _perform_security_analysis(self, part: Part, visual_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security-focused analysis"""
        
        security_prompt = f"""
Based on the visual analysis provided, perform a comprehensive security assessment of this architecture:

Visual Analysis Context:
{json.dumps(visual_analysis, indent=2)}

Security Analysis Tasks:

1. **Component Security Classification**: For each component, determine:
   - Component type (database, application, gateway, cloud_service, load_balancer, etc.) - use your architectural knowledge
   - Security domain (Internet, Intranet, DMZ, Cloud, Unknown)
   - Technology security profile
   - Exposure level and attack surface
   - Data sensitivity level

2. **Connection Security Assessment**: For each connection, evaluate:
   - Protocol security (HTTPS, HTTP, TCP, etc.)
   - Encryption requirements
   - Authentication/authorization needs
   - Security boundary crossings

3. **Architecture Security Patterns**: Identify:
   - Security zones and boundaries
   - Defense in depth implementation
   - Network segmentation effectiveness
   - Access control mechanisms

4. **Risk Assessment**: Identify:
   - High-risk components and connections
   - Potential attack vectors
   - Data exposure risks
   - Compliance gaps

5. **Security Recommendations**: Provide:
   - Immediate security improvements
   - Architecture enhancements
   - Technology upgrades
   - Process improvements

Return structured security analysis:
{{
    "component_security": [
        {{
            "component_name": "name",
            "component_type": "database|application|gateway|cloud_service|load_balancer|etc",
            "security_domain": "Internet|Intranet|DMZ|Cloud|Unknown",
            "technology": "identified_technology",
            "exposure_level": "High|Medium|Low",
            "security_concerns": ["list_of_concerns"]
        }}
    ],
    "connection_security": [
        {{
            "source": "source",
            "target": "target",
            "protocol": "protocol",
            "security_level": "Secure|Insecure|Unknown",
            "encryption": "Encrypted|Unencrypted|Unknown",
            "security_concerns": ["list_of_concerns"]
        }}
    ],
    "security_zones": [
        {{
            "zone_name": "zone",
            "security_level": "High|Medium|Low",
            "components": ["component_list"],
            "boundary_controls": ["security_controls"]
        }}
    ],
    "security_concerns": ["overall_security_issues"],
    "recommendations": ["actionable_security_recommendations"]
}}
"""
        
        response = await self.security_agent.generate_content_async([security_prompt, part])
        return self._parse_json_response(response.text)
    
    def _combine_analyses(self, visual_analysis: Dict[str, Any], security_analysis: Dict[str, Any], 
                         filename: str, session_id: str, mime_type: str) -> ArchitectureAnalysis:
        """Combine visual and security analyses into final result"""
        
        # Convert visual components to Component objects
        components = []
        for comp_data in visual_analysis.get('visual_components', []):
            # Find corresponding security data
            security_data = next(
                (s for s in security_analysis.get('component_security', []) 
                 if s.get('component_name') == comp_data.get('name')), 
                {}
            )
            
            component = Component(
                name=comp_data.get('name', ''),
                type=security_data.get('component_type') or comp_data.get('component_type') or 'component',
                technology=security_data.get('technology'),
                domain=security_data.get('security_domain'),
                description=comp_data.get('text_content'),
                position=comp_data.get('position'),
                confidence=0.9  # High confidence for AI analysis
            )
            components.append(component)
        
        # Convert visual connections to Connection objects
        connections = []
        for conn_data in visual_analysis.get('visual_connections', []):
            # Find corresponding security data
            security_data = next(
                (s for s in security_analysis.get('connection_security', [])
                 if s.get('source') == conn_data.get('source') and s.get('target') == conn_data.get('target')),
                {}
            )
            
            connection = Connection(
                source=conn_data.get('source', ''),
                target=conn_data.get('target', ''),
                protocol=security_data.get('protocol'),
                description=conn_data.get('labels', [None])[0] if conn_data.get('labels') else None,
                security_level=security_data.get('security_level'),
                confidence=0.9
            )
            connections.append(connection)
        
        # Extract technologies and domains
        technologies = list(set(
            security_analysis.get('technology_indicators', []) +
            [comp.technology for comp in components if comp.technology]
        ))
        
        domains = list(set(
            [comp.domain for comp in components if comp.domain]
        ))
        
        return ArchitectureAnalysis(
            components=components,
            connections=connections,
            technologies=technologies,
            domains=domains,
            security_concerns=security_analysis.get('security_concerns', []),
            recommendations=security_analysis.get('recommendations', []),
            metadata={
                'filename': filename,
                'session_id': session_id,
                'analysis_timestamp': datetime.now().isoformat(),
                'mime_type': mime_type,
                'analysis_method': 'ai_vision_security_analysis'
            }
        )
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response with fallback"""
        try:
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Fallback to empty structure
        return {
            'visual_components': [],
            'visual_connections': [],
            'visual_zones': [],
            'extracted_text': [],
            'technology_indicators': []
        }
    
    async def generate_security_report(self, analysis_json: str) -> str:
        """Generate comprehensive security report from JSON analysis data"""
        try:
            # Parse the JSON string back to a dictionary
            analysis_data = json.loads(analysis_json)
            
            # Extract data from the JSON structure
            components = analysis_data.get('components', [])
            connections = analysis_data.get('connections', [])
            technologies = analysis_data.get('technologies', [])
            domains = analysis_data.get('domains', [])
            security_concerns = analysis_data.get('security_concerns', [])
            recommendations = analysis_data.get('recommendations', [])
            metadata = analysis_data.get('metadata', {})
            
            report = f"""
# Architecture Security Analysis Report

## Executive Summary
Analysis of **{metadata.get('filename', 'unknown')}** identified:
- **{len(components)}** components across **{len(domains)}** security domains
- **{len(connections)}** inter-component connections
- **{len(technologies)}** distinct technologies
- **{len(security_concerns)}** security concerns identified

## Technology Stack
{', '.join(technologies) if technologies else 'No specific technologies identified'}

## Security Domains
{', '.join(domains) if domains else 'No security domains identified'}

## Component Analysis by Security Domain
"""
            
            # Group components by domain
            components_by_domain = {}
            for comp in components:
                domain = comp.get('domain', 'unknown')
                if domain not in components_by_domain:
                    components_by_domain[domain] = []
                components_by_domain[domain].append(comp)
            
            for domain, comps in components_by_domain.items():
                report += f"\n### {domain.title()} Domain ({len(comps)} components)\n"
                for comp in comps:
                    report += f"- **{comp.get('name', 'Unknown')}** ({comp.get('type', 'Unknown')})"
                    if comp.get('technology'):
                        report += f" - {comp.get('technology')}"
                    if comp.get('description'):
                        report += f": {comp.get('description')}"
                    report += "\n"
            
            # Connection analysis
            report += f"\n## Data Flow Analysis\n"
            report += f"**{len(connections)}** connections identified:\n\n"
            
            for conn in connections:
                report += f"- **{conn.get('source', 'Unknown')}** → **{conn.get('target', 'Unknown')}**"
                if conn.get('protocol'):
                    report += f" ({conn.get('protocol')})"
                if conn.get('security_level'):
                    report += f" - Security: {conn.get('security_level')}"
                if conn.get('description'):
                    report += f" - {conn.get('description')}"
                report += "\n"
            
            # Security concerns
            if security_concerns:
                report += f"\n## Security Concerns\n"
                for i, concern in enumerate(security_concerns, 1):
                    report += f"{i}. {concern}\n"
            
            # Recommendations
            if recommendations:
                report += f"\n## Security Recommendations\n"
                for i, rec in enumerate(recommendations, 1):
                    report += f"{i}. {rec}\n"
            
            report += f"\n---\n*Analysis performed on {metadata.get('analysis_timestamp', 'unknown')} using AI vision and security analysis*"
            
            return report
            
        except json.JSONDecodeError as e:
            return f"Error parsing analysis data: {e}"
        except Exception as e:
            return f"Error generating report: {e}"

# Note: ArchitectureAnalyzer instance and sub-agent are now created in cybersecurity_agent.py
# to properly inject the artifact service dependency


        