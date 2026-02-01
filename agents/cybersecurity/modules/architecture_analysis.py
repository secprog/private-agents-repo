"""
Advanced Architecture Security Analysis
Analyzes architecture diagrams for security threats, vulnerabilities, and compliance
"""

import logging
import json

from google.adk.models import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from .prompts import (
    get_security_context_instructions,
    get_threat_analysis_instructions,
    get_attack_path_instructions,
    get_compliance_instructions,
    get_recommendations_instructions,
)
from .models import (
    SecurityContext,
    ThreatAnalysisResult,
    AttackPathResult,
    ComplianceResult,
    RecommendationsResult,
)
import os

logger = logging.getLogger(__name__)


class ArchitectureAnalysis:
    """
    Security-focused architecture analyzer.
    Accepts generic visual data from vision agent and performs multi-phase security assessment.
    """

    def __init__(self):
        logger.info("ArchitectureAnalyzer initialized for security analysis")

    async def identify_security_context(
        self,
        components_json: str,
        connections_json: str,
        zones_json: str,
        boundaries_json: str,
        annotations_json: str = "[]",
        legend_mappings_json: str = "[]",
        line_crossings_json: str = "[]"
    ) -> str:
        """
        First pass: Interpret generic visual data into security context.
        Identifies technologies, IT roles, protocols, encryption status, and security zones
        from the domain-neutral visual facts provided by the vision agent.

        Args:
            components_json: Visual components (generic visual facts)
            connections_json: Visual connections with colors, patterns, markers, text labels
            zones_json: Visual zones from vision agent
            boundaries_json: Visual boundaries with visual_style, color, line_style, text_labels
            annotations_json: Optional text annotations, notes, callouts
            legend_mappings_json: Optional legend symbol-to-meaning mappings
            line_crossings_json: Optional line crossing analysis

        Returns:
            JSON string containing SecurityContext
        """
        try:
            logger.info("Starting security context identification")
            self._validate_json_input("components", components_json)
            self._validate_json_input("connections", connections_json)
            self._validate_json_input("zones", zones_json)
            self._validate_json_input("boundaries", boundaries_json)

            context = self._build_visual_data_context(
                components_json, connections_json, zones_json,
                boundaries_json, annotations_json, legend_mappings_json,
                line_crossings_json
            )

            return await self._call_llm(
                context,
                get_security_context_instructions(),
                SecurityContext,
                "security context identification"
            )
        except Exception as e:
            logger.error(f"Failed to identify security context: {e}")
            raise

    async def analyze_threats_and_vulnerabilities(
        self,
        security_context_json: str,
        components_json: str,
        connections_json: str,
        boundaries_json: str,
    ) -> str:
        """
        Second pass: Identify threats and vulnerabilities using the security context.

        Args:
            security_context_json: SecurityContext from identify_security_context
            components_json: Original visual components for reference
            connections_json: Original visual connections for reference
            boundaries_json: Original visual boundaries for reference

        Returns:
            JSON string containing threats and vulnerabilities
        """
        try:
            logger.info("Starting threat and vulnerability analysis")
            self._validate_json_input("security_context", security_context_json)

            context = f"""# Threat and Vulnerability Analysis

## Security Context (interpreted from visual data)
```json
{security_context_json}
```

## Original Visual Components
```json
{components_json}
```

## Original Visual Connections
```json
{connections_json}
```

## Original Visual Boundaries
```json
{boundaries_json}
```

Analyze the security context above and identify all threats and vulnerabilities.
"""
            return await self._call_llm(
                context,
                get_threat_analysis_instructions(),
                ThreatAnalysisResult,
                "threat and vulnerability analysis"
            )
        except Exception as e:
            logger.error(f"Failed to analyze threats: {e}")
            raise

    async def analyze_attack_paths(
        self,
        security_context_json: str,
        threats_json: str,
    ) -> str:
        """
        Third pass: Analyze attack paths using security context and identified threats.

        Args:
            security_context_json: SecurityContext from identify_security_context
            threats_json: Threats and vulnerabilities from analyze_threats_and_vulnerabilities

        Returns:
            JSON string containing attack paths
        """
        try:
            logger.info("Starting attack path analysis")
            self._validate_json_input("security_context", security_context_json)
            self._validate_json_input("threats", threats_json)

            context = f"""# Attack Path Analysis

## Security Context
```json
{security_context_json}
```

## Identified Threats and Vulnerabilities
```json
{threats_json}
```

Trace all possible attack paths through this architecture.
"""
            return await self._call_llm(
                context,
                get_attack_path_instructions(),
                AttackPathResult,
                "attack path analysis"
            )
        except Exception as e:
            logger.error(f"Failed to analyze attack paths: {e}")
            raise

    async def assess_compliance(
        self,
        security_context_json: str,
    ) -> str:
        """
        Fourth pass: Assess compliance against security frameworks.

        Args:
            security_context_json: SecurityContext from identify_security_context

        Returns:
            JSON string containing compliance checks
        """
        try:
            logger.info("Starting compliance assessment")
            self._validate_json_input("security_context", security_context_json)

            context = f"""# Compliance Assessment

## Security Context
```json
{security_context_json}
```

Assess this architecture against all relevant compliance frameworks.
"""
            return await self._call_llm(
                context,
                get_compliance_instructions(),
                ComplianceResult,
                "compliance assessment"
            )
        except Exception as e:
            logger.error(f"Failed to assess compliance: {e}")
            raise

    async def generate_recommendations(
        self,
        security_context_json: str,
        threats_json: str,
        attack_paths_json: str,
        compliance_json: str,
    ) -> str:
        """
        Final pass: Synthesize all findings into recommendations, posture assessment, and summary.

        Args:
            security_context_json: SecurityContext from identify_security_context
            threats_json: Threats and vulnerabilities from analyze_threats_and_vulnerabilities
            attack_paths_json: Attack paths from analyze_attack_paths
            compliance_json: Compliance checks from assess_compliance

        Returns:
            JSON string containing recommendations, security posture, and summary
        """
        try:
            logger.info("Starting recommendation generation")
            self._validate_json_input("security_context", security_context_json)
            self._validate_json_input("threats", threats_json)
            self._validate_json_input("attack_paths", attack_paths_json)
            self._validate_json_input("compliance", compliance_json)

            context = f"""# Security Recommendations Synthesis

## Security Context
```json
{security_context_json}
```

## Threats and Vulnerabilities
```json
{threats_json}
```

## Attack Paths
```json
{attack_paths_json}
```

## Compliance Findings
```json
{compliance_json}
```

Synthesize all findings into prioritized recommendations, an overall security posture assessment, and an executive summary.
"""
            return await self._call_llm(
                context,
                get_recommendations_instructions(),
                RecommendationsResult,
                "recommendation generation"
            )
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            raise

    # --- Private helpers ---

    async def _call_llm(
        self,
        context: str,
        system_instruction: str,
        output_schema,
        step_name: str,
    ) -> str:
        """Call LLM with given context and system instruction."""
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
                system_instruction=system_instruction,
                max_output_tokens=50000,
                response_mime_type="application/json",
            ),
        )
        if output_schema:
            llm_request.set_output_schema(output_schema)

        logger.info(f"Calling LLM for {step_name}")

        response_text = ""
        async for llm_response in llm.generate_content_async(llm_request, stream=False):
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

        if not response_text:
            raise ValueError(f"Empty response from LLM during {step_name}")

        # Validate JSON
        try:
            json.loads(response_text)
            logger.info(f"{step_name} complete: {len(response_text)} chars")
            return response_text
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {step_name} response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise

    def _validate_json_input(self, name: str, json_str: str) -> None:
        """Validate that input is valid JSON"""
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for {name}: {e}")
            raise ValueError(f"Invalid JSON input for {name}: {e}")

    def _build_visual_data_context(
        self,
        components_json: str,
        connections_json: str,
        zones_json: str,
        boundaries_json: str,
        annotations_json: str,
        legend_mappings_json: str,
        line_crossings_json: str,
    ) -> str:
        """Build context string with all visual data for security context identification."""
        return """# Visual Data for Security Context Identification

Interpret the following GENERIC VISUAL DATA and identify IT roles, technologies, protocols, encryption, and security zones.

## Visual Components
```json
{components}
```

## Visual Connections
```json
{connections}
```

## Visual Zones
```json
{zones}
```

## Visual Boundaries
```json
{boundaries}
```

## Annotations
```json
{annotations}
```

## Legend Mappings
```json
{legend_mappings}
```

## Line Crossings
```json
{line_crossings}
```
""".format(
            components=components_json,
            connections=connections_json,
            zones=zones_json,
            boundaries=boundaries_json,
            annotations=annotations_json,
            legend_mappings=legend_mappings_json,
            line_crossings=line_crossings_json,
        )
