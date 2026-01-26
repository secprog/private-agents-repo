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
    get_diagram_comparison_instructions,
    get_enhancement_instructions,
    get_plantuml_export_instructions,
    get_mermaid_export_instructions,
    get_drawio_export_instructions,
    get_image_quality_assessment_instructions,
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
    DiagramComparison,
    EnhancedAnalysis,
    OCRTextResult,
    Position,
    PlantUMLExport,
    MermaidExport,
    DrawIOExport,
    ImageQualityAssessment,
    ImageRegion,
    LegendExtraction,
    LineCrossing,
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

    async def compare_diagrams(
        self, user_id: str, session_id: str, filename1: str, filename2: str
    ) -> str:
        """Compare two diagrams and identify differences"""
        try:
            logger.info(
                f"Starting diagram comparison: {filename1} vs {filename2} for session_id={session_id}"
            )

            part1 = await self.artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename1,
                version=None,
            )

            part2 = await self.artifact_service.load_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename2,
                version=None,
            )

            if not part1 or not part1.inline_data:
                raise ValueError(f"Could not load artifact: {filename1}")
            if not part2 or not part2.inline_data:
                raise ValueError(f"Could not load artifact: {filename2}")

            comparison_prompt = f"""Compare these two diagrams:
- Diagram 1: {filename1}
- Diagram 2: {filename2}

Identify all differences, similarities, and changes."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=comparison_prompt),
                            part1,
                            types.Part.from_text(text="--- Diagram 2 ---"),
                            part2,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_diagram_comparison_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(DiagramComparison)
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
                logger.error(f"Failed to parse comparison response: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to compare diagrams: {e}")
            raise

    async def enhance_analysis(
        self, user_id: str, session_id: str, filename: str, initial_analysis_json: str
    ) -> str:
        """Enhance and improve initial visual analysis"""
        try:
            logger.info(
                f"Starting analysis enhancement for session_id={session_id}, filename={filename}"
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

            enhancement_prompt = f"""Review and enhance the following initial analysis for file "{filename}".

Initial Analysis:
{initial_analysis_json}

Improve the analysis by correcting errors, filling gaps, and improving confidence scores."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=enhancement_prompt),
                            part,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_enhancement_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(EnhancedAnalysis)
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
                logger.error(f"Failed to parse enhancement response: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to enhance analysis: {e}")
            raise

    async def extract_text_with_paddleocr(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Extract text using PaddleOCR (more accurate than GPT for text)"""
        try:
            logger.info(
                f"Starting PaddleOCR text extraction for session_id={session_id}, filename={filename}"
            )

            # Get the file path from artifact service
            artifact_root = os.getenv("ARTIFACT_ROOT_DIR", "./my_artifacts")
            file_path = os.path.join(
                artifact_root, APP_NAME, user_id, session_id, filename
            )

            if not os.path.exists(file_path):
                logger.warning(
                    f"PaddleOCR source file missing at {file_path}. Falling back to GPT OCR."
                )
                return await self.extract_text_from_image(user_id, session_id, filename)

            # Use PaddleOCR MCP tool for detailed extraction
            try:
                # Note: PaddleOCR is accessed via MCP protocol, not direct import
                # This is a placeholder for MCP tool integration
                # In production, this would use the MCP client to call the PaddleOCR tool

                # For now, we'll fall back to GPT OCR
                logger.warning(
                    "PaddleOCR MCP integration pending - falling back to GPT"
                )
                return await self.extract_text_from_image(user_id, session_id, filename)

                # TODO: Implement proper MCP tool call like:
                # from mcp_client import call_tool
                # ocr_result = await call_tool("paddleocr", "ocr",
                #                              input_data=file_path, output_mode="detailed")

                # Convert PaddleOCR result to our format

                text_results = []
                if isinstance(ocr_result, str):
                    # Parse the result if it's a string
                    ocr_data = (
                        json.loads(ocr_result)
                        if ocr_result.startswith("{") or ocr_result.startswith("[")
                        else {"text": ocr_result}
                    )
                else:
                    ocr_data = ocr_result

                # Extract text from PaddleOCR format
                if isinstance(ocr_data, list):
                    for item in ocr_data:
                        if isinstance(item, dict) and "text" in item:
                            bbox = item.get("box", [[0, 0], [0, 0], [0, 0], [0, 0]])
                            x_coords = [p[0] for p in bbox]
                            y_coords = [p[1] for p in bbox]

                            text_results.append(
                                {
                                    "text": item["text"],
                                    "position": {
                                        "x": min(x_coords),
                                        "y": min(y_coords),
                                        "width": max(x_coords) - min(x_coords),
                                        "height": max(y_coords) - min(y_coords),
                                    },
                                    "confidence": item.get("confidence", 1.0),
                                    "source": "paddleocr",
                                }
                            )
                elif isinstance(ocr_data, dict) and "text" in ocr_data:
                    text_results.append(
                        {
                            "text": ocr_data["text"],
                            "position": {"x": 0, "y": 0, "width": 0, "height": 0},
                            "confidence": ocr_data.get("confidence", 1.0),
                            "source": "paddleocr",
                        }
                    )
                elif isinstance(ocr_data, str):
                    text_results.append(
                        {
                            "text": ocr_data,
                            "position": {"x": 0, "y": 0, "width": 0, "height": 0},
                            "confidence": 1.0,
                            "source": "paddleocr",
                        }
                    )

                # This code is unreachable due to early return above
                # Keeping structure for when MCP integration is completed
                return json.dumps(text_results)

            except Exception as e:
                logger.warning(f"PaddleOCR MCP error: {e}, falling back to GPT")
                return await self.extract_text_from_image(user_id, session_id, filename)

        except Exception as e:
            logger.error(f"Failed to extract text with PaddleOCR: {e}")
            raise

    async def extract_text_with_consensus(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Use both GPT and PaddleOCR, merge results with confidence scoring"""
        try:
            logger.info(
                f"Starting consensus text extraction for session_id={session_id}, filename={filename}"
            )

            # Run both methods (they can run in parallel conceptually, but we'll do sequential for simplicity)
            gpt4o_task = self.extract_text_from_image(user_id, session_id, filename)
            paddleocr_task = self.extract_text_with_paddleocr(
                user_id, session_id, filename
            )

            # Gather both results, capturing exceptions
            gpt4o_result, paddleocr_result = await asyncio.gather(
                gpt4o_task, paddleocr_task, return_exceptions=True
            )

            # Handle if one or both failed
            if isinstance(gpt4o_result, Exception) and isinstance(
                paddleocr_result, Exception
            ):
                logger.error(
                    f"Both extraction methods failed: GPT: {gpt4o_result}, PaddleOCR: {paddleocr_result}"
                )
                raise Exception(f"All text extraction methods failed: {gpt4o_result}")
            elif isinstance(gpt4o_result, Exception):
                logger.warning(
                    f"GPT extraction failed: {gpt4o_result}, using PaddleOCR only"
                )
                if isinstance(paddleocr_result, str):
                    return paddleocr_result
                else:
                    raise paddleocr_result
            elif isinstance(paddleocr_result, Exception):
                logger.warning(
                    f"PaddleOCR extraction failed: {paddleocr_result}, using GPT only"
                )
                if isinstance(gpt4o_result, str):
                    return gpt4o_result
                else:
                    raise gpt4o_result

            # Parse results
            gpt4o_texts = (
                json.loads(gpt4o_result)
                if isinstance(gpt4o_result, str)
                else gpt4o_result
            )
            paddleocr_texts = (
                json.loads(paddleocr_result)
                if isinstance(paddleocr_result, str)
                else paddleocr_result
            )

            # Merge results with consensus logic
            merged_texts = []
            conflicts = []

            # Simple merge: take all unique texts, prefer higher confidence
            text_map = {}

            for item in gpt4o_texts if isinstance(gpt4o_texts, list) else []:
                text = item.get("text", "").strip()
                if text:
                    text_map[text] = {**item, "source": "gpt4o"}

            for item in paddleocr_texts if isinstance(paddleocr_texts, list) else []:
                text = item.get("text", "").strip()
                if text:
                    if text in text_map:
                        # Conflict - both found same text
                        existing = text_map[text]
                        new_conf = item.get("confidence", 0.5)
                        old_conf = existing.get("confidence", 0.5)

                        if new_conf > old_conf:
                            text_map[text] = {**item, "source": "consensus"}
                        else:
                            text_map[text]["source"] = "consensus"
                    else:
                        text_map[text] = {**item, "source": "paddleocr"}

            merged_texts = list(text_map.values())
            overall_confidence = (
                sum(t.get("confidence", 0.5) for t in merged_texts) / len(merged_texts)
                if merged_texts
                else 0.0
            )

            result = {
                "texts": merged_texts,
                "conflicts": conflicts,
                "overall_confidence": overall_confidence,
            }

            return json.dumps(result)

        except Exception as e:
            logger.error(f"Failed consensus text extraction: {e}")
            raise

    async def export_to_plantuml(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        components_json: str,
        connections_json: str,
        zones_json: str,
    ) -> str:
        """Convert visual analysis to PlantUML diagram code"""
        try:
            logger.info(
                f"Exporting to PlantUML for session_id={session_id}, filename={filename}"
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

            export_prompt = f"""Convert the following visual analysis to PlantUML code for file "{filename}".

Components:
{components_json}

Connections:
{connections_json}

Zones:
{zones_json}

Generate PlantUML code that represents this architecture diagram."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=export_prompt),
                            part,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_plantuml_export_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(PlantUMLExport)
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
                logger.error(f"Failed to parse PlantUML export: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to export to PlantUML: {e}")
            raise

    async def export_to_mermaid(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        components_json: str,
        connections_json: str,
        zones_json: str,
    ) -> str:
        """Convert visual analysis to Mermaid diagram code"""
        try:
            logger.info(
                f"Exporting to Mermaid for session_id={session_id}, filename={filename}"
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

            export_prompt = f"""Convert the following visual analysis to Mermaid diagram code for file "{filename}".

Components:
{components_json}

Connections:
{connections_json}

Zones:
{zones_json}

Generate Mermaid code that represents this architecture diagram."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=export_prompt),
                            part,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_mermaid_export_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(MermaidExport)
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
                logger.error(f"Failed to parse Mermaid export: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to export to Mermaid: {e}")
            raise

    async def export_to_drawio(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        components_json: str,
        connections_json: str,
        zones_json: str,
    ) -> str:
        """Convert visual analysis to draw.io XML format"""
        try:
            logger.info(
                f"Exporting to draw.io for session_id={session_id}, filename={filename}"
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

            export_prompt = f"""Convert the following visual analysis to draw.io XML format for file "{filename}".

Components:
{components_json}

Connections:
{connections_json}

Zones:
{zones_json}

Generate draw.io (diagrams.net) XML code that represents this architecture diagram.
Use proper mxGraph XML format with accurate positioning and appropriate styles."""

            llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5.1"))
            llm_request = LlmRequest(
                model=llm.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=export_prompt),
                            part,
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=get_drawio_export_instructions(),
                    max_output_tokens=50000,
                    response_mime_type="application/json",
                ),
            )

            llm_request.set_output_schema(DrawIOExport)
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
                logger.error(f"Failed to parse draw.io export: {e}")
                return json.dumps(
                    {"raw_response": response_text, "parse_error": str(e)}
                )

        except Exception as e:
            logger.error(f"Failed to export to draw.io: {e}")
            raise

    async def assess_image_quality(
        self, user_id: str, session_id: str, filename: str
    ) -> str:
        """Assess image quality for analysis suitability"""
        try:
            logger.info(
                f"Assessing image quality for session_id={session_id}, filename={filename}"
            )
            result = await self._perform_visual_analysis(
                user_id,
                session_id,
                filename,
                ImageQualityAssessment,
                get_image_quality_assessment_instructions(),
            )
            return result

        except Exception as e:
            logger.error(f"Failed to assess image quality: {e}")
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

    # async def analyze_by_regions(
    #     self, user_id: str, session_id: str, filename: str
    # ) -> str:
    #     """Perform region-based analysis for complex diagrams"""
    #     try:
    #         logger.info(
    #             f"Starting region-based analysis for session_id={session_id}, filename={filename}"
    #         )

    #         # First, identify regions
    #         regions_json = await self.identify_regions(user_id, session_id, filename)
    #         regions = json.loads(regions_json)

    #         if not isinstance(regions, list):
    #             raise ValueError("Expected list of regions")

    #         # For now, just perform comprehensive analysis on the whole image
    #         # In a full implementation, you would:
    #         # 1. Split the image into regions
    #         # 2. Analyze each region separately
    #         # 3. Merge the results

    #         logger.info(
    #             f"Identified {len(regions)} regions, performing comprehensive analysis"
    #         )

    #         # Analyze all regions in parallel (simplified: analyze whole image)
    #         components_task = self.analyze_visual_components(
    #             user_id, session_id, filename
    #         )
    #         connections_task = self.analyze_visual_connections(
    #             user_id, session_id, filename
    #         )
    #         zones_task = self.analyze_visual_zones(user_id, session_id, filename)

    #         components_json, connections_json, zones_json = await asyncio.gather(
    #             components_task, connections_task, zones_task
    #         )

    #         result = {
    #             "regions": regions,
    #             "merged_components": json.loads(components_json),
    #             "merged_connections": json.loads(connections_json),
    #             "merged_zones": json.loads(zones_json),
    #             "overall_quality": 0.85,  # Placeholder
    #         }

    #         return json.dumps(result)

    #     except Exception as e:
    #         logger.error(f"Failed region-based analysis: {e}")
    #         raise

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
