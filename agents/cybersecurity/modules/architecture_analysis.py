"""
Advanced Architecture Security Analysis
Analyzes architecture diagrams for security threats, vulnerabilities, and compliance
"""

import logging
import json

from typing import Optional

from google.adk.models import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from .prompts import get_comprehensive_security_analysis_instructions
from .models import ComprehensiveSecurityAnalysis
import os

logger = logging.getLogger(__name__)


class ArchitectureAnalysis:
    """
    Security-focused architecture analyzer.
    Accepts comprehensive visual analysis from vision agent and performs security assessment.
    """

    def __init__(self):
        logger.info("ArchitectureAnalyzer initialized for security analysis")

    async def analyze_architecture_security(
        self,
        components_json: str,
        connections_json: str,
        zones_json: str,
        boundaries_json: str,
        technologies_json: str = "[]",
        relationships_json: str = "[]",
        annotations_json: str = "[]",
        legend_mappings_json: str = "[]",
        line_crossings_json: str = "[]"
    ) -> str:
        """
        Comprehensive security analysis of architecture using rich vision data.

        Args:
            components_json: Visual components from vision agent
            connections_json: Visual connections from vision agent
            zones_json: Visual zones from vision agent
            boundaries_json: Visual boundaries from vision agent
            technologies_json: Detected technologies from vision agent
            relationships_json: Inferred relationships from vision agent
            annotations_json: Optional annotations from vision agent
            legend_mappings_json: Optional legend mappings from vision agent
            line_crossings_json: Optional line crossings from vision agent

        Returns:
            JSON string containing ComprehensiveSecurityAnalysis
        """
        try:
            logger.info("Starting comprehensive security analysis")
            
            # Validate inputs
            self._validate_json_input("components", components_json)
            self._validate_json_input("connections", connections_json)
            self._validate_json_input("zones", zones_json)
            self._validate_json_input("boundaries", boundaries_json)
            self._validate_json_input("technologies", technologies_json)
            self._validate_json_input("relationships", relationships_json)
            
            # Build comprehensive context for LLM
            context = self._build_analysis_context(
                components_json,
                connections_json,
                zones_json,
                boundaries_json,
                technologies_json,
                relationships_json,
                annotations_json,
                legend_mappings_json,
                line_crossings_json
            )
            
            logger.info(f"Analysis context built: {len(context)} characters")
            
            # Perform security analysis using LLM
            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5.1"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=context)]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_comprehensive_security_analysis_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )
            llm_request.set_output_schema(ComprehensiveSecurityAnalysis)
            
            logger.info("Calling LLM for security analysis")

            # generate_content_async returns an async generator even when stream=False
            response_text = ""
            async for llm_response in llm.generate_content_async(
                llm_request, stream=False
            ):
                error_message = getattr(llm_response, "error_message", None)
                if error_message:
                    error_code = getattr(llm_response, "error_code", None)
                    prefix = f"{error_code}: " if error_code else ""
                    raise ValueError(f"{prefix}{error_message}")

                if llm_response.content and llm_response.content.parts:
                    for part in llm_response.content.parts:
                        text_value = getattr(part, "text", None)
                        if text_value:
                            response_text += text_value

            # Extract and parse response
            if not response_text:
                raise ValueError("Empty response from LLM")
            
            # Parse and validate JSON
            try:
                security_analysis = json.loads(response_text)
                logger.info(
                    f"Security analysis complete: "
                    f"{len(security_analysis.get('threats', []))} threats, "
                    f"{len(security_analysis.get('vulnerabilities', []))} vulnerabilities, "
                    f"{len(security_analysis.get('attack_paths', []))} attack paths, "
                    f"{len(security_analysis.get('recommendations', []))} recommendations"
                )
                return response_text
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Response text: {response_text[:500]}...")
                raise
                
        except Exception as e:
            logger.error(f"Failed to analyze architecture security: {e}")
            raise
    
    def _validate_json_input(self, name: str, json_str: str) -> None:
        """Validate that input is valid JSON"""
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for {name}: {e}")
            raise ValueError(f"Invalid JSON input for {name}: {e}")
    
    def _build_analysis_context(
        self,
        components_json: str,
        connections_json: str,
        zones_json: str,
        boundaries_json: str,
        technologies_json: str,
        relationships_json: str,
        annotations_json: str,
        legend_mappings_json: str,
        line_crossings_json: str
    ) -> str:
        """Build comprehensive context string for LLM analysis"""

        context = """# Architecture Security Analysis Request

Please analyze the following architecture data and provide a comprehensive security assessment.

## Visual Components
Components in the architecture (servers, databases, APIs, etc.):
```json
{components}
```

## Visual Connections
Connections and data flows between components:
```json
{connections}
```

## Visual Zones
Logical zones and regions in the architecture:
```json
{zones}
```

## Visual Boundaries
Visual boundaries and enclosures (zones, regions, groupings):
Note: Interpret text_labels, colors, and visual styles to identify security zones, trust boundaries, network segments, etc.
```json
{boundaries}
```

## Detected Technologies
Technologies, frameworks, and cloud services identified:
```json
{technologies}
```

## Inferred Relationships
Logical relationships and dependencies not explicitly shown:
```json
{relationships}
```

## Annotations (if available)
Text annotations, notes, and warnings:
```json
{annotations}
```

## Legend Mappings (if available)
Symbol-to-meaning mappings from diagram legend:
```json
{legend_mappings}
```

## Line Crossings (if available)
Network topology and line crossing analysis:
```json
{line_crossings}
```

---

IMPORTANT: The Visual Boundaries section contains generic visual data. You must INTERPRET:
- text_labels like "DMZ", "Public", "Internet-Facing" → security zones
- Red/orange dashed boundaries → often indicate exposed/public zones
- Blue/green boundaries → often indicate protected/internal zones
- Components_inside → which components are in each security zone

Based on this comprehensive data, perform a thorough security analysis and identify threats, vulnerabilities, attack paths, compliance issues, and provide actionable recommendations.
"""

        return context.format(
            components=components_json,
            connections=connections_json,
            zones=zones_json,
            boundaries=boundaries_json,
            technologies=technologies_json,
            relationships=relationships_json,
            annotations=annotations_json,
            legend_mappings=legend_mappings_json,
            line_crossings=line_crossings_json
        )
