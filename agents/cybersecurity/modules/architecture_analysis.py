"""
Advanced Architecture Analysis using AI Vision and Multi-modal Processing
"""

import logging
import json

from typing import Dict, Any

# Use the LLM directly for efficient analysis
from google.adk.artifacts import BaseArtifactService
from google.adk_community.models.openai_llm import OpenAI
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from google.genai.types import Part
from .prompts import (
    get_vision_analysis_instructions,
)
from .models import VisualAnalysisResponse

logger = logging.getLogger(__name__)
APP_NAME = "orquestrator"


class ArchitectureAnalysis:

    def __init__(self, artifact_service: BaseArtifactService):
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

    async def _perform_visual_analysis(self, part: Part, filename: str) -> Dict[str, Any]:

        visual_prompt = f"""Analyze this architecture diagram with advanced computer vision capabilities. 
        For the file "{filename}", provide a comprehensive visual analysis in json format."""

        llm = OpenAI(model="gpt-4o")
        # Use Pydantic model for visual analysis response schema
        visual_schema = VisualAnalysisResponse

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
                system_instruction=get_vision_analysis_instructions(),
                temperature=0.1,
                max_output_tokens=16384,
                response_mime_type="application/json",
            ),
        )

        # Set output schema using the method (handles structured output properly)
        llm_request.set_output_schema(visual_schema)
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
        return json.dumps(json.loads(response_text))
