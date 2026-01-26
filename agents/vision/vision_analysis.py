"""
Vision Analysis Module - Specialized visual analysis for architecture diagrams
"""

import logging
import json
import os
import asyncio
import re
from typing import Any


from google.adk.artifacts import BaseArtifactService
from google.adk.models import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from google.genai.types import Part
from pydantic import BaseModel
import os

from prompts import (
    get_component_analysis_instructions,
    get_connection_analysis_instructions,
    get_zone_analysis_instructions,
    get_text_extraction_instructions,
    get_validation_instructions,
    get_layout_analysis_instructions,
    get_styling_analysis_instructions,
    get_annotation_extraction_instructions,
    get_region_identification_instructions,
    get_legend_extraction_instructions,
    get_line_crossing_detection_instructions,
    get_boundary_extraction_instructions,
)
from models import (
    VisualComponent,
    VisualConnection,
    VisualZone,
    TextExtraction,
    ValidationResult,
    LayoutStructure,
    StylingPattern,
    Annotation,
    ImageRegion,
    LegendExtraction,
    LineCrossing,
    OCRTextResult,
    Position,
    VisualBoundary,
)

logger = logging.getLogger(__name__)
APP_NAME = "orquestrator"


class VisionAnalysis:

    def __init__(self, artifact_service: BaseArtifactService):
        self.artifact_service = artifact_service
        logger.info(
            f"VisionAnalysis initialized with artifact service: {type(artifact_service)}"
        )
        service_type = getattr(artifact_service, "service_type", None)
        if service_type is not None:
            logger.info(f"Artifact service type: {service_type}")
        underlying_service = getattr(artifact_service, "artifact_service", None)
        if underlying_service is not None:
            logger.info(
                f"Underlying artifact service: {type(underlying_service)}"
            )

    async def _perform_visual_analysis(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        visual_schema: type[BaseModel],
        system_instruction: str,
    ) -> str:
        """Perform visual analysis using LLM with structured output"""
        def _is_missing(value: str) -> bool:
            """Detect empty or placeholder context values."""
            if value is None:
                return True
            if isinstance(value, str):
                cleaned = value.strip().lower()
                return cleaned in {"", "unknown", "none", "null", "undefined"}
            return False

        # Guard against missing context so the LLM isn't called with placeholders
        if _is_missing(user_id) or _is_missing(session_id) or _is_missing(filename):
            logger.warning(
                "Visual analysis requested without required artifact context "
                f"(user_id={user_id}, session_id={session_id}, filename={filename})"
            )
            return json.dumps(
                {
                    "error": "NO_IMAGE_PROVIDED",
                    "message": "Please upload/select an image before requesting visual analysis.",
                }
            )
        visual_prompt = f"""Analyze this architecture diagram with advanced computer vision capabilities. 
        For the file "{filename}", provide a comprehensive visual analysis in json format."""

        part = await self.artifact_service.load_artifact(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
            version=None,
        )

        if not part or not part.inline_data:
            logger.error(
                f"Could not load artifact: {filename} from session {session_id}"
            )
            # Return a JSON error that can be gracefully handled by the frontend/agent
            return json.dumps({
                "error": f"Could not load artifact: {filename}", 
                "message": "Please make sure you have uploaded an image before asking for analysis.",
                "code": "ARTIFACT_NOT_FOUND" 
            })
        else:
            logger.info(
                f"Successfully loaded artifact: {filename} (type: {part.inline_data.mime_type})"
            )

        llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))

        # Create LlmRequest (ADK's request object)
        llm_request = LlmRequest(
            model=llm.model,
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
                system_instruction=system_instruction,
                max_output_tokens=50000,
                response_mime_type="application/json",
            ),
        )

        # Set output schema using the method (handles structured output properly)
        llm_request.set_output_schema(visual_schema)
        # Call the LLM - this returns an async generator
        response_text = ""
        finish_reason = None
        response_count = 0
        response_debug_info = []
        async for llm_response in llm.generate_content_async(llm_request, stream=False):
            response_count += 1
            error_message = getattr(llm_response, "error_message", None)
            if error_message:
                error_code = getattr(llm_response, "error_code", None)
                error_prefix = f"{error_code}: " if error_code else ""
                full_error = f"{error_prefix}{error_message}"
                logger.error(f"LLM returned error: {full_error}")
                raise ValueError(full_error)
            content_summary = []
            if llm_response.content and llm_response.content.parts:
                # Collect all text parts in case there are multiple
                text_parts = []
                for content_part in llm_response.content.parts:
                    part_summary: dict[str, Any] = {
                        "part_type": type(content_part).__name__,
                    }
                    text_value = getattr(content_part, "text", None)
                    if text_value:
                        text_parts.append(text_value)
                        part_summary.update(
                            {
                                "has_text": True,
                                "text_length": len(text_value),
                                "text_preview": text_value[:200],
                            }
                        )
                    else:
                        part_summary["has_text"] = False

                    inline_data = getattr(content_part, "inline_data", None)
                    if inline_data is not None:
                        part_summary.update(
                            {
                                "has_inline_data": True,
                                "inline_mime_type": getattr(
                                    inline_data, "mime_type", None
                                ),
                            }
                        )
                        inline_data_value = getattr(inline_data, "data", None)
                        if inline_data_value is not None:
                            part_summary["inline_data_length"] = len(inline_data_value)
                    else:
                        part_summary["has_inline_data"] = False

                    content_summary.append(part_summary)
                if text_parts:
                    response_text += "".join(text_parts)  # Accumulate, don't replace
            else:
                content_summary.append({"has_content": False})

            # Check finish reason to detect truncation (update from last response)
            if hasattr(llm_response, "finish_reason"):
                finish_reason = llm_response.finish_reason

            response_debug_info.append(
                {
                    "index": response_count,
                    "finish_reason": finish_reason,
                    "error_message": error_message,
                    "content_summary": content_summary,
                }
            )

        if not response_text:
            logger.error("Empty response from LLM")

            summary_payload = response_debug_info or [{"note": "No responses emitted"}]
            summary_text = ""
            try:
                summary_text = json.dumps(
                    summary_payload, ensure_ascii=False, default=str
                )
                logger.error("LLM raw response summary: %s", summary_text)
            except Exception as debug_exc:
                logger.error(f"Failed to serialize response debug info: {debug_exc}")
                logger.error(f"Raw debug info repr: {summary_payload!r}")
                summary_text = repr(summary_payload)

            raise ValueError(
                f"Empty response from LLM - no text content received. Summary: {summary_text}"
            )

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

        # Parse JSON response - handle cases where there might be extra data
        try:
            # Try to parse as JSON
            parsed_response = json.loads(response_text)
            return json.dumps(parsed_response)
        except json.JSONDecodeError as e:
            # If parsing fails, try to extract the first valid JSON object
            logger.warning(
                f"JSON parsing error: {e}. Attempting to extract valid JSON from response."
            )

            # Try to find the first complete JSON object
            # Look for the first '{' and try to find matching '}'
            start_idx = response_text.find("{")
            if start_idx != -1:
                # Try to find the matching closing brace
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == "{":
                        brace_count += 1
                    elif response_text[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break

                if end_idx > start_idx:
                    # Extract the JSON substring
                    json_substring = response_text[start_idx:end_idx]
                    try:
                        parsed_response = json.loads(json_substring)
                        logger.info(
                            f"Successfully extracted JSON from response (char {start_idx} to {end_idx})"
                        )
                        return json.dumps(parsed_response)
                    except json.JSONDecodeError:
                        logger.error(
                            f"Failed to parse extracted JSON substring: {json_substring[:200]}..."
                        )

            # If all else fails, return the response as-is (it might already be valid)
            logger.error(
                f"Could not parse response as JSON. Returning raw response. Error: {e}"
            )
            logger.debug(f"Response text (first 500 chars): {response_text[:500]}")
            # Return as a JSON string containing the raw text
            return json.dumps({"raw_response": response_text, "parse_error": str(e)})

    async def run_core_analysis_parallel(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """
        Run the components, connections, and zones analysis passes in parallel
        and return all results in a single JSON payload.
        """
        try:
            logger.info(
                f"Starting bundled core analysis for session_id={session_id}, filename={filename}"
            )

            components_task = self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                VisualComponent,
                get_component_analysis_instructions(),
            )
            connections_task = self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                VisualConnection,
                get_connection_analysis_instructions(),
            )
            zones_task = self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                VisualZone,
                get_zone_analysis_instructions(),
            )

            components_json, connections_json, zones_json = await asyncio.gather(
                components_task, connections_task, zones_task
            )

            bundled_result = {
                "components": json.loads(components_json),
                "connections": json.loads(connections_json),
                "zones": json.loads(zones_json),
                "components_json": components_json,
                "connections_json": connections_json,
                "zones_json": zones_json,
            }

            return json.dumps(bundled_result)

        except Exception as e:
            logger.error(f"Failed to run bundled core analysis: {e}")
            raise

    async def analyze_visual_components(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Analyze the visual components of the image"""
        try:
            logger.info(
                f"Starting visual components analysis for session_id={session_id}, filename={filename}"
            )

            # Perform visual analysis for components
            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                VisualComponent,
                get_component_analysis_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to analyze visual components: {e}")
            raise

    async def analyze_visual_connections(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Analyze the visual connections of the image"""
        try:
            logger.info(
                f"Starting visual connections analysis for session_id={session_id}, filename={filename}"
            )

            # Perform visual analysis for connections
            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                VisualConnection,
                get_connection_analysis_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to analyze visual connections: {e}")
            raise

    async def analyze_visual_zones(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Analyze the visual zones of the image"""
        try:
            logger.info(
                f"Starting visual zones analysis for session_id={session_id}, filename={filename}"
            )

            # Perform visual analysis for zones
            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                VisualZone,
                get_zone_analysis_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to analyze visual zones: {e}")
            raise

    async def extract_text_from_image(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Extract all text from the image using OCR"""
        try:
            logger.info(
                f"Starting text extraction for session_id={session_id}, filename={filename}"
            )

            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                TextExtraction,
                get_text_extraction_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to extract text: {e}")
            raise

    async def validate_visual_analysis(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        components_json: str,
        connections_json: str,
        zones_json: str,
    ) -> str:
        """Validate and check quality of visual analysis results"""
        try:
            logger.info(
                f"Starting validation for session_id={session_id}, filename={filename}"
            )

            part = await self.artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                version=None,
            )

            if not part or not part.inline_data:
                raise ValueError(
                    f"Could not load artifact: {filename} from session {session_id}"
                )

            # Create prompt with analysis results
            validation_prompt = f"""Validate the following visual analysis results for file "{filename}".

Components:
{components_json}

Connections:
{connections_json}

Zones:
{zones_json}

Analyze these results and identify issues, inconsistencies, and areas for improvement."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=validation_prompt),
                            part,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_validation_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(ValidationResult)
            response_text = ""
            async for llm_response in llm.generate_content_async(
                llm_request, stream=False
            ):
                if llm_response.content and llm_response.content.parts:
                    text_parts = [
                        part.text
                        for part in llm_response.content.parts
                        if hasattr(part, "text") and part.text
                    ]
                    if text_parts:
                        response_text += "".join(text_parts)

            if not response_text:
                raise ValueError("Empty response from LLM")

            try:
                parsed_response = json.loads(response_text)
                return json.dumps(parsed_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse validation response: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to validate analysis: {e}")
            raise

    async def analyze_layout(self, user_id: str, session_id: str, filename: str) -> str:
        """Analyze diagram layout, hierarchy, and structure"""
        try:
            logger.info(
                f"Starting layout analysis for session_id={session_id}, filename={filename}"
            )

            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                LayoutStructure,
                get_layout_analysis_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to analyze layout: {e}")
            raise

    async def analyze_styling(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Analyze color coding, styling patterns, and visual conventions"""
        try:
            logger.info(
                f"Starting styling analysis for session_id={session_id}, filename={filename}"
            )

            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                StylingPattern,
                get_styling_analysis_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to analyze styling: {e}")
            raise

    async def extract_annotations(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Extract annotations, notes, callouts, and warnings"""
        try:
            logger.info(
                f"Starting annotation extraction for session_id={session_id}, filename={filename}"
            )

            part = await self.artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                version=None,
            )

            if not part or not part.inline_data:
                raise ValueError(
                    f"Could not load artifact: {filename} from session {session_id}"
                )

            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                Annotation,
                get_annotation_extraction_instructions()
            )
            return result

        except Exception as e:
            logger.error(f"Failed to extract annotations: {e}")
            raise

    async def identify_regions(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Identify logical regions in the diagram for detailed analysis"""
        try:
            logger.info(
                f"Identifying regions for session_id={session_id}, filename={filename}"
            )

            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                ImageRegion,
                get_region_identification_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to identify regions: {e}")
            raise

    async def extract_legend_mappings(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Extract and parse diagram legends (symbol-to-meaning mappings)"""
        try:
            logger.info(
                f"Starting legend extraction for session_id={session_id}, filename={filename}"
            )

            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                LegendExtraction,
                get_legend_extraction_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to extract legend mappings: {e}")
            raise

    async def detect_line_crossings(
        self, user_id: str, session_id: str, filename: str, connections_json: str
    ) -> str:
        """Detect line crossings and determine if they are actual intersections"""
        try:
            logger.info(
                f"Starting line crossing detection for session_id={session_id}, filename={filename}"
            )

            part = await self.artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                version=None,
            )

            if not part or not part.inline_data:
                raise ValueError(
                    f"Could not load artifact: {filename} from session {session_id}"
                )

            crossing_prompt = f"""Analyze line crossings in the diagram for file "{filename}".

Known Connections:
{connections_json}

Identify where lines cross and determine if they actually connect or just visually overlap."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=crossing_prompt),
                            part,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_line_crossing_detection_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(LineCrossing)
            response_text = ""
            async for llm_response in llm.generate_content_async(
                llm_request, stream=False
            ):
                if llm_response.content and llm_response.content.parts:
                    text_parts = [
                        part.text
                        for part in llm_response.content.parts
                        if hasattr(part, "text") and part.text
                    ]
                    if text_parts:
                        response_text += "".join(text_parts)

            if not response_text:
                raise ValueError("Empty response from LLM")

            try:
                parsed_response = json.loads(response_text)
                return json.dumps(parsed_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse line crossing response: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to detect line crossings: {e}")
            raise

    async def extract_boundaries(
        self, user_id: str, session_id: str, filename: str, components_json: str | None = None
    ) -> str:
        """Extract visual boundaries and enclosures from diagrams"""
        try:
            logger.info(
                f"Starting boundary extraction for session_id={session_id}, filename={filename}"
            )

            part = await self.artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                version=None,
            )

            if not part or not part.inline_data:
                raise ValueError(
                    f"Could not load artifact: {filename} from session {session_id}"
                )

            # Optionally include components context if provided
            if components_json:
                boundary_prompt = f"""Extract visual boundaries and enclosures for file "{filename}".

Known Components:
{components_json}

Extract all visual boundaries, zones, and grouping regions."""
            else:
                boundary_prompt = f"""Extract visual boundaries and enclosures for file "{filename}".

Analyze the diagram to find all boundaries, zones, and grouping regions."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=boundary_prompt),
                            part,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_boundary_extraction_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(VisualBoundary)
            response_text = ""
            async for llm_response in llm.generate_content_async(
                llm_request, stream=False
            ):
                if llm_response.content and llm_response.content.parts:
                    text_parts = [
                        part.text
                        for part in llm_response.content.parts
                        if hasattr(part, "text") and part.text
                    ]
                    if text_parts:
                        response_text += "".join(text_parts)

            if not response_text:
                raise ValueError("Empty response from LLM")

            try:
                parsed_response = json.loads(response_text)
                return json.dumps(parsed_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse boundary response: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to extract boundaries: {e}")
            raise

