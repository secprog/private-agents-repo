"""
Advanced Architecture Analysis using AI Vision and Multi-modal Processing
"""

import logging
import base64
import json

from typing import Dict, Any

from google.genai.types import Part, Blob

logger = logging.getLogger(__name__)

class ArchitectureAnalyzer:
    """Advanced architecture analyzer using AI vision and multi-modal processing"""
    
    def __init__(self, artifact_service=None):        
        # Store the artifact service for loading files
        self.artifact_service = artifact_service
        logger.info(f"ArchitectureAnalyzer initialized with artifact service: {type(artifact_service)}")
        if hasattr(artifact_service, 'service_type'):
            logger.info(f"Artifact service type: {artifact_service.service_type}")
        if hasattr(artifact_service, 'artifact_service'):
            logger.info(f"Underlying artifact service: {type(artifact_service.artifact_service)}")
        
        # Store the specialized instructions for different analysis tasks
        self.vision_instructions = self._get_vision_analysis_instructions()
        self.security_instructions = self._get_security_analysis_instructions()
    
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
    
    async def security_analysis(self, part: Part, visual_analysis: Dict[str, Any]) -> str:
        """Compreensive Security analysis of the architecture"""
        security_analysis = await self._perform_security_analysis(part, visual_analysis)
        return json.dumps(security_analysis)


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
            
            visual_analysis = await self._perform_visual_analysis(part, filename)
            return json.dumps(visual_analysis)
            
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

6. **Confidence Assessment**: For each component and connection, provide a confidence score (0.0-1.0) based on:
   - Clarity of visual elements
   - Text readability and completeness
   - Uniqueness of component identification
   - Ambiguity in connections or relationships

Return your analysis as structured JSON following the provided schema, including confidence scores for each element.
"""
        
        # Use the LLM directly for efficient analysis
        from google.adk.models.registry import LLMRegistry
        from google.adk.models.llm_request import LlmRequest
        from google.genai import types
        
        llm = LLMRegistry.new_llm("gemini-2.0-flash")
        
        # Define JSON schema for visual analysis response
        visual_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Visual Analysis Response",
            "type": "object",
            "properties": {
                "visual_components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "component_type": {"type": "string", "enum": ["database", "application", "gateway", "cloud_service", "load_balancer", "firewall", "proxy", "cache", "queue", "storage", "compute", "network", "monitoring", "other"]},
                            "visual_type": {"type": "string", "enum": ["box", "circle", "icon", "diamond", "cylinder", "cloud", "other"]},
                            "position": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"}
                                },
                                "required": ["x", "y"]
                            },
                            "text_content": {"type": "string"},
                            "visual_group": {"type": "string"},
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence score for component identification (0.0-1.0)"
                            }
                        },
                        "required": ["name", "component_type", "visual_type", "position", "text_content", "confidence"]
                    }
                },
                "visual_connections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "connection_type": {"type": "string", "enum": ["arrow", "line", "dotted", "dashed", "thick", "bidirectional", "other"]},
                            "direction": {"type": "string", "enum": ["unidirectional", "bidirectional", "unknown"]},
                            "labels": {"type": "array", "items": {"type": "string"}},
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence score for connection identification (0.0-1.0)"
                            }
                        },
                        "required": ["source", "target", "connection_type", "direction", "labels", "confidence"]
                    }
                },
                "visual_zones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "boundary_type": {"type": "string", "enum": ["dashed_line", "box", "color", "border", "background", "other"]},
                            "components": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "boundary_type", "components"]
                    }
                },
                "extracted_text": {"type": "array", "items": {"type": "string"}},
                "technology_indicators": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["visual_components", "visual_connections", "visual_zones", "extracted_text", "technology_indicators"]
        }
        
        # Create LlmRequest (ADK's request object)
        llm_request = LlmRequest(
            model="gemini-2.0-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=visual_prompt),
                        part  # The image part
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.vision_instructions,
                temperature=0.1,
                response_json_schema=visual_schema,
                response_mime_type="application/json"
            )
        )
        
        # Call the LLM - this returns an async generator
        response_text = ""
        async for llm_response in llm.generate_content_async(llm_request, stream=False):
            if llm_response.content and llm_response.content.parts:
                response_text = llm_response.content.parts[0].text
                break  # For non-streaming, there's only one response
        
        return self._parse_json_response(response_text)
    
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

6. **Confidence Assessment**: For each security assessment, provide a confidence score (0.0-1.0) based on:
   - Clarity of component identification
   - Technology recognition accuracy
   - Security domain classification certainty
   - Risk assessment confidence

Return structured security analysis following the provided JSON schema, including confidence scores for each assessment.
"""
        
        # Use the LLM directly for efficient analysis
        from google.adk.models.registry import LLMRegistry
        from google.adk.models.llm_request import LlmRequest
        from google.genai import types
        
        llm = LLMRegistry.new_llm("gemini-2.0-flash")
        
        # Define JSON schema for security analysis response
        security_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Security Analysis Response",
            "type": "object",
            "properties": {
                "component_security": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "component_name": {"type": "string"},
                            "component_type": {"type": "string", "enum": ["database", "application", "gateway", "cloud_service", "load_balancer", "firewall", "proxy", "cache", "queue", "storage", "compute", "network", "monitoring", "other"]},
                            "security_domain": {"type": "string", "enum": ["Internet", "Intranet", "DMZ", "Cloud", "Unknown"]},
                            "technology": {"type": "string"},
                            "exposure_level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                            "security_concerns": {"type": "array", "items": {"type": "string"}},
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence score for security assessment (0.0-1.0)"
                            }
                        },
                        "required": ["component_name", "component_type", "security_domain", "exposure_level", "security_concerns", "confidence"]
                    }
                },
                "connection_security": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "protocol": {"type": "string"},
                            "security_level": {"type": "string", "enum": ["Secure", "Insecure", "Unknown"]},
                            "encryption": {"type": "string", "enum": ["Encrypted", "Unencrypted", "Unknown"]},
                            "security_concerns": {"type": "array", "items": {"type": "string"}},
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence score for connection security assessment (0.0-1.0)"
                            }
                        },
                        "required": ["source", "target", "protocol", "security_level", "encryption", "security_concerns", "confidence"]
                    }
                },
                "security_zones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "zone_name": {"type": "string"},
                            "security_level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                            "components": {"type": "array", "items": {"type": "string"}},
                            "boundary_controls": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["zone_name", "security_level", "components", "boundary_controls"]
                    }
                },
                "security_concerns": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["component_security", "connection_security", "security_zones", "security_concerns", "recommendations"]
        }
        
        # Create LlmRequest (ADK's request object)
        llm_request = LlmRequest(
            model="gemini-2.0-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=security_prompt),
                        part  # The image part
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.security_instructions,
                temperature=0.1,
                response_json_schema=security_schema,
                response_mime_type="application/json"
            )
        )
        
        # Call the LLM - this returns an async generator
        response_text = ""
        async for llm_response in llm.generate_content_async(llm_request, stream=False):
            if llm_response.content and llm_response.content.parts:
                response_text = llm_response.content.parts[0].text
                break  # For non-streaming, there's only one response
        
        return self._parse_json_response(response_text)
    
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response with fallback"""
        try:
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON response: {text}")
    