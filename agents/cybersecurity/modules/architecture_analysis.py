"""
Advanced Architecture Analysis using AI Vision and Multi-modal Processing
"""

import logging
import json

from typing import Dict, Any
from google.genai.types import Part
from .models import VisualAnalysisResponse, SecurityAnalysisResponse

logger = logging.getLogger(__name__)
APP_NAME = "orquestrator"


class ArchitectureAnalyzer:
    """Advanced architecture analyzer using AI vision and multi-modal processing"""

    def __init__(self, artifact_service):
        # Store the artifact service for loading files
        self.artifact_service = artifact_service
        logger.info(
            f"ArchitectureAnalyzer initialized with artifact service: {type(artifact_service)}"
        )
        if hasattr(artifact_service, "service_type"):
            logger.info(f"Artifact service type: {artifact_service.service_type}")
        if hasattr(artifact_service, "artifact_service"):
            logger.info(
                f"Underlying artifact service: {type(artifact_service.artifact_service)}"
            )

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

**CRITICAL: You MUST return your response as valid JSON ONLY. Do NOT use markdown code blocks, do NOT include explanations or descriptions outside the JSON. Your response must start with {{ and end with }} and contain ONLY valid JSON that matches the provided schema.**
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

    async def security_analysis(
        self, part: Part, visual_analysis: Dict[str, Any]
    ) -> str:
        """Compreensive Security analysis of the architecture"""
        security_analysis = await self._perform_security_analysis(part, visual_analysis)
        return json.dumps(security_analysis)

    async def analyze_architecture(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Comprehensive architecture analysis using AI vision and security expertise"""
        try:
            logger.info(
                f"Starting architecture analysis for session_id={session_id}, filename={filename}"
            )

            # Load artifact using artifact_service directly
            logger.info(
                f"Loading artifact with params: app_name={APP_NAME}, user_id={user_id}, session_id={session_id}, filename={filename}"
            )
            part = await self.artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                version=None,
            )

            if not part or not part.inline_data:
                logger.error(f"Could not load artifact")
                logger.error(
                    f"Load params were: app_name={APP_NAME}, user_id={user_id}, session_id={session_id}, filename={filename}"
                )
                raise ValueError(
                    f"Could not load artifact: {filename} from session {session_id}"
                )

            logger.info(
                f"Successfully loaded artifact: {filename} (type: {part.inline_data.mime_type})"
            )

            visual_analysis = await self._perform_visual_analysis(part, filename)
            return json.dumps(visual_analysis)

        except Exception as e:
            logger.error(f"Failed to analyze architecture: {e}")
            raise

    async def _perform_visual_analysis(
        self, part: Part, filename: str
    ) -> Dict[str, Any]:
        """Perform detailed visual analysis of the architecture diagram"""

        visual_prompt = f"""
**CRITICAL INSTRUCTION: You MUST return ONLY valid JSON. Do NOT include any markdown formatting, explanations, descriptions, or text outside of the JSON. Your ENTIRE response must be valid JSON that can be parsed directly.**

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

**CRITICAL: You MUST return JSON that EXACTLY matches this structure. Do NOT create your own structure. The response MUST have these exact top-level fields:**

{{
  "visual_components": [
    {{
      "name": "string",
      "component_type": "database|application|gateway|cloud_service|load_balancer|firewall|proxy|cache|queue|storage|compute|network|monitoring|other",
      "visual_type": "box|circle|icon|diamond|cylinder|cloud|other",
      "position": {{"x": number, "y": number}},
      "text_content": "string",
      "visual_group": "string",
      "confidence": 0.0-1.0
    }}
  ],
  "visual_connections": [
    {{
      "source": "string",
      "target": "string",
      "connection_type": "arrow|line|dotted|dashed|thick|bidirectional|other",
      "direction": "unidirectional|bidirectional|unknown",
      "labels": ["string"],
      "confidence": 0.0-1.0
    }}
  ],
  "visual_zones": [
    {{
      "name": "string",
      "boundary_type": "dashed_line|box|color|border|background|other",
      "components": ["string"]
    }}
  ],
  "extracted_text": ["string"],
  "technology_indicators": ["string"]
}}

**ALL fields are REQUIRED. Every component MUST have all fields including position, visual_group, and confidence. Every connection MUST have all fields including labels and confidence.**

**REMEMBER: Return ONLY the JSON object. No markdown code blocks, no explanations, no text before or after. Start with {{ and end with }}.**
"""

        # Use the LLM directly for efficient analysis
        from google.adk.models.registry import LLMRegistry
        from google.adk.models.llm_request import LlmRequest
        from google.genai import types

        llm = LLMRegistry.new_llm("gemini-2.5-flash-preview-09-2025 ")

        # Use Pydantic model for visual analysis response schema
        visual_schema = VisualAnalysisResponse
        
        # Convert Pydantic model to JSON schema dict for response_json_schema
        visual_schema_dict = visual_schema.model_json_schema()

        # Create LlmRequest (ADK's request object)
        llm_request = LlmRequest(
            model="gemini-2.5-flash-preview-09-2025",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=visual_prompt),
                        part,  # The image part
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.vision_instructions,
                temperature=0.1,
                max_output_tokens=65535,
                response_mime_type="application/json",
                response_json_schema=visual_schema_dict,  # Also set in config
            ),
        )

        llm_request.set_output_schema(visual_schema)  # Set via method as well

        # Call the LLM - this returns an async generator
        response_text = ""
        finish_reason = None
        response_count = 0
        async for llm_response in llm.generate_content_async(llm_request, stream=False):
            response_count += 1
            if llm_response.content and llm_response.content.parts:
                # Collect all text parts in case there are multiple
                text_parts = []
                for part in llm_response.content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    response_text += "".join(text_parts)  # Accumulate, don't replace

            # Check finish reason to detect truncation (update from last response)
            if hasattr(llm_response, "finish_reason"):
                finish_reason = llm_response.finish_reason
            elif hasattr(llm_response, "candidates") and llm_response.candidates:
                if hasattr(llm_response.candidates[0], "finish_reason"):
                    finish_reason = llm_response.candidates[0].finish_reason

        if not response_text:
            logger.error("Empty response from LLM")
            raise ValueError("Empty response from LLM - no text content received")

        # Check if response was truncated
        if finish_reason and finish_reason in [
            "MAX_TOKENS",
            "LENGTH",
            "MAX_OUTPUT_TOKENS",
        ]:
            logger.warning(f"Response may be truncated. Finish reason: {finish_reason}")
            logger.warning(f"Response length: {len(response_text)} characters")

        logger.debug(
            f"Collected {response_count} responses, total length: {len(response_text)}, finish_reason: {finish_reason}"
        )
        return self._parse_json_response(response_text)

    async def _perform_security_analysis(
        self, part: Part, visual_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
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

**CRITICAL: You MUST return JSON that EXACTLY matches this structure. Do NOT create your own structure. The response MUST have these exact top-level fields:**

{{
  "component_security": [
    {{
      "component_name": "string",
      "component_type": "database|application|gateway|cloud_service|load_balancer|firewall|proxy|cache|queue|storage|compute|network|monitoring|other",
      "security_domain": "Internet|Intranet|DMZ|Cloud|Unknown",
      "technology": "string",
      "exposure_level": "High|Medium|Low",
      "security_concerns": ["string"],
      "confidence": 0.0-1.0
    }}
  ],
  "connection_security": [
    {{
      "source": "string",
      "target": "string",
      "protocol": "string",
      "security_level": "Secure|Insecure|Unknown",
      "encryption": "Encrypted|Unencrypted|Unknown",
      "security_concerns": ["string"],
      "confidence": 0.0-1.0
    }}
  ],
  "security_zones": [
    {{
      "zone_name": "string",
      "security_level": "High|Medium|Low",
      "components": ["string"],
      "boundary_controls": ["string"]
    }}
  ],
  "security_concerns": ["string"],
  "recommendations": ["string"]
}}

**ALL fields are REQUIRED. Every component_security entry MUST have all fields including confidence. Every connection_security entry MUST have all fields including confidence.**
"""

        # Use the LLM directly for efficient analysis
        from google.adk.models.registry import LLMRegistry
        from google.adk.models.llm_request import LlmRequest
        from google.genai import types

        llm = LLMRegistry.new_llm("gemini-2.5-flash-preview-09-2025")

        # Use Pydantic model for security analysis response schema
        security_schema = SecurityAnalysisResponse
        
        # Convert Pydantic model to JSON schema dict for response_json_schema
        security_schema_dict = security_schema.model_json_schema()

        # Create LlmRequest (ADK's request object)
        llm_request = LlmRequest(
            model="gemini-2.5-flash-preview-09-2025",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=security_prompt),
                        part,  # The image part
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=self.security_instructions,
                temperature=0.1,
                response_mime_type="application/json",
                max_output_tokens=65535,
                response_json_schema=security_schema_dict,  # Also set in config
            ),
        )
        llm_request.set_output_schema(security_schema)  # Set via method as well
        # Call the LLM - this returns an async generator
        response_text = ""
        finish_reason = None
        response_count = 0
        async for llm_response in llm.generate_content_async(llm_request, stream=False):
            response_count += 1
            if llm_response.content and llm_response.content.parts:
                # Collect all text parts in case there are multiple
                text_parts = []
                for part in llm_response.content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    response_text += "".join(text_parts)  # Accumulate, don't replace

            # Check finish reason to detect truncation (update from last response)
            if hasattr(llm_response, "finish_reason"):
                finish_reason = llm_response.finish_reason
            elif hasattr(llm_response, "candidates") and llm_response.candidates:
                if hasattr(llm_response.candidates[0], "finish_reason"):
                    finish_reason = llm_response.candidates[0].finish_reason

        if not response_text:
            logger.error("Empty response from LLM")
            raise ValueError("Empty response from LLM - no text content received")

        # Check if response was truncated
        if finish_reason and finish_reason in [
            "MAX_TOKENS",
            "LENGTH",
            "MAX_OUTPUT_TOKENS",
        ]:
            logger.warning(f"Response may be truncated. Finish reason: {finish_reason}")
            logger.warning(f"Response length: {len(response_text)} characters")

        logger.debug(
            f"Collected {response_count} responses, total length: {len(response_text)}, finish_reason: {finish_reason}"
        )
        return self._parse_json_response(response_text)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response with fallback - detects incomplete JSON and handles markdown"""
        if not text:
            raise ValueError("Empty response text")

        # Log the raw response for debugging
        logger.debug(f"Raw response (first 500 chars): {text[:500]}")
        logger.debug(f"Raw response (last 500 chars): {text[-500:]}")

        # Remove markdown code blocks if present
        text_cleaned = text.strip()
        if text_cleaned.startswith("```json"):
            text_cleaned = text_cleaned[7:].strip()
        elif text_cleaned.startswith("```"):
            text_cleaned = text_cleaned[3:].strip()
        if text_cleaned.endswith("```"):
            text_cleaned = text_cleaned[:-3].strip()

        # Check if response looks like JSON (starts with {)
        if not text_cleaned.strip().startswith("{"):
            logger.error(f"Response does not appear to be JSON. First 200 chars: {text_cleaned[:200]}")
            raise ValueError(
                f"Response is not JSON format. The model returned text/markdown instead of JSON. "
                f"Please check the prompt and schema configuration. Response preview: {text_cleaned[:500]}"
            )

        try:
            json_start = text_cleaned.find("{")
            json_end = text_cleaned.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_str = text_cleaned[json_start:json_end]
                logger.debug(f"Extracted JSON string (length: {len(json_str)})")

                # Check if JSON appears incomplete by counting brackets
                open_braces = json_str.count("{")
                close_braces = json_str.count("}")
                open_brackets = json_str.count("[")
                close_brackets = json_str.count("]")

                if open_braces != close_braces or open_brackets != close_brackets:
                    logger.error(
                        f"Incomplete JSON detected. Braces: {open_braces} open, {close_braces} close. Brackets: {open_brackets} open, {close_brackets} close"
                    )
                    logger.error(f"JSON preview (last 500 chars): ...{json_str[-500:]}")
                    raise ValueError(
                        f"Incomplete JSON response - missing closing brackets. Response may have been truncated. JSON length: {len(json_str)}"
                    )

                return json.loads(json_str)
            else:
                raise ValueError(f"Could not find JSON boundaries in response.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Error at position {e.pos}: {e.msg}")
            # Check if error suggests incomplete JSON
            if e.msg and ("Expecting" in e.msg or "Unterminated" in e.msg):
                logger.error(
                    f"JSON appears incomplete. Last 200 chars: ...{text[-200:]}"
                )
                raise ValueError(
                    f"Incomplete JSON response - parsing failed at position {e.pos}: {e.msg}. Response may have been truncated."
                )
            raise ValueError(
                f"Invalid JSON response. Error: {e.msg} at position {e.pos if hasattr(e, 'pos') else 'unknown'}"
            )
