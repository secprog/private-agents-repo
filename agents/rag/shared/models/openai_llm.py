"""OpenAI integration for GPT models in the ADK framework."""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from typing import Any
from typing import Dict
from typing import Literal
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

import openai
from google.genai import types
from typing_extensions import override

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse

if TYPE_CHECKING:
    from google.adk.models.llm_request import LlmRequest

__all__ = ["OpenAI"]

logger = logging.getLogger(__name__)


def to_openai_role(role: Optional[str]) -> Literal["user", "assistant", "system"]:
    """Converts ADK role to OpenAI role."""
    if role == "model":
        return "assistant"
    elif role == "system":
        return "system"
    else:
        return "user"


def to_google_genai_finish_reason(
    openai_finish_reason: Optional[str],
) -> types.FinishReason:
    """Converts OpenAI finish reason to Google GenAI finish reason."""
    if openai_finish_reason == "stop":
        return "STOP"
    elif openai_finish_reason == "length":
        return "MAX_TOKENS"
    elif openai_finish_reason == "content_filter":
        return "SAFETY"
    elif openai_finish_reason == "tool_calls":
        return "STOP"
    else:
        return "FINISH_REASON_UNSPECIFIED"


def _is_image_part(part: types.Part) -> bool:
    """Checks if a part contains image data."""
    return (
        part.inline_data
        and part.inline_data.mime_type
        and part.inline_data.mime_type.startswith("image")
    )


async def part_to_openai_content(
    part: types.Part,
    openai_instance: Optional[OpenAI] = None,
) -> Union[Dict[str, Any], str]:
    """Converts ADK Part to OpenAI content format.

    OpenAI supports:
    - Text content
    - Images (base64 encoded)
    - PDF files (via Files API or base64 for vision models)
    - Other documents (via Files API or base64 for vision models)
    """
    if part.text:
        return {"type": "text", "text": part.text}
    elif part.function_call:
        # Function calls are handled separately in the message structure
        return {"type": "text", "text": f"Function call: {part.function_call.name}"}
    elif part.function_response:
        # Function responses are handled separately in the message structure
        return {
            "type": "text",
            "text": f"Function response: {part.function_response.response}",
        }
    elif part.inline_data or part.file_data:
        # Handle file data using the OpenAI instance's file handling
        if openai_instance:
            return await openai_instance._handle_file_data(part)
        else:
            # Fallback to simple base64 encoding if no OpenAI instance provided
            if part.inline_data:
                mime_type = part.inline_data.mime_type or "application/octet-stream"
                data = base64.b64encode(part.inline_data.data).decode()

                if mime_type.startswith("image/"):
                    return {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{data}"},
                    }
                else:
                    return {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{data}"},
                    }
            else:
                return {
                    "type": "text",
                    "text": f"[FILE REFERENCE: {part.file_data.display_name or 'unnamed'}]",
                }
    elif part.executable_code:
        return {"type": "text", "text": f"```python\n{part.executable_code.code}\n```"}
    elif part.code_execution_result:
        return {
            "type": "text",
            "text": f"Execution Result:\n```\n{part.code_execution_result.output}\n```",
        }
    else:
        # Fallback for unsupported parts
        logger.warning(f"Unsupported part type in OpenAI conversion: {type(part)}")
        return {"type": "text", "text": f"[UNSUPPORTED CONTENT: {str(part)[:100]}...]"}


async def content_to_openai_message(
    content: types.Content,
    openai_instance: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    """Converts ADK Content to OpenAI message format."""
    message_content = []
    tool_calls = []
    tool_call_id = None

    for part in content.parts or []:
        if part.function_call:
            # Handle function calls
            tool_calls.append(
                {
                    "id": part.function_call.id or f"call_{len(tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": part.function_call.name,
                        "arguments": (
                            json.dumps(part.function_call.args)
                            if part.function_call.args
                            else "{}"
                        ),
                    },
                }
            )
        elif part.function_response:
            # Handle function responses
            tool_call_id = part.function_response.id
            message_content.append(
                {
                    "type": "text",
                    "text": (
                        json.dumps(part.function_response.response)
                        if isinstance(part.function_response.response, dict)
                        else str(part.function_response.response)
                    ),
                }
            )
        else:
            # Handle regular content
            openai_content = await part_to_openai_content(part, openai_instance)
            if isinstance(openai_content, dict):
                message_content.append(openai_content)
            else:
                message_content.append({"type": "text", "text": openai_content})

    message = {"role": to_openai_role(content.role), "content": message_content}

    if tool_calls:
        message["tool_calls"] = tool_calls
    if tool_call_id:
        message["tool_call_id"] = tool_call_id

    return message


def function_declaration_to_openai_tool(
    function_declaration: types.FunctionDeclaration,
) -> Dict[str, Any]:
    """Converts ADK function declaration to OpenAI tool format."""
    properties = {}
    required_params = []

    if function_declaration.parameters:
        if function_declaration.parameters.properties:
            for key, value in function_declaration.parameters.properties.items():
                value_dict = value.model_dump(exclude_none=True)
                # Convert type string to OpenAI format
                if "type" in value_dict and value_dict["type"] == "string":
                    value_dict["type"] = "string"
                elif "type" in value_dict and value_dict["type"] == "number":
                    value_dict["type"] = "number"
                elif "type" in value_dict and value_dict["type"] == "boolean":
                    value_dict["type"] = "boolean"
                elif "type" in value_dict and value_dict["type"] == "array":
                    value_dict["type"] = "array"
                elif "type" in value_dict and value_dict["type"] == "object":
                    value_dict["type"] = "object"
                properties[key] = value_dict

        if function_declaration.parameters.required:
            required_params = function_declaration.parameters.required

    function_schema = {
        "name": function_declaration.name,
        "description": function_declaration.description or "",
        "parameters": {
            "type": "object",
            "properties": properties,
        },
    }

    if required_params:
        function_schema["parameters"]["required"] = required_params

    return {"type": "function", "function": function_schema}


def openai_response_to_llm_response(
    response: Any,
) -> LlmResponse:
    """Converts OpenAI response to ADK LlmResponse."""
    logger.info("Received response from OpenAI.")
    logger.debug(f"OpenAI response: {response}")

    # Extract content from response
    content_parts = []

    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        message = choice.message

        if hasattr(message, "content") and message.content:
            content_parts.append(types.Part(text=message.content))

        # Handle tool calls
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.type == "function":
                    function_args = {}
                    if tool_call.function.arguments:
                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            function_args = {"arguments": tool_call.function.arguments}

                    content_parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                id=tool_call.id,
                                name=tool_call.function.name,
                                args=function_args,
                            )
                        )
                    )

    # Create content
    content = (
        types.Content(role="model", parts=content_parts) if content_parts else None
    )

    # Extract usage metadata
    usage_metadata = None
    if hasattr(response, "usage") and response.usage:
        usage_metadata = types.GenerateContentResponseUsageMetadata(
            prompt_token_count=response.usage.prompt_tokens,
            candidates_token_count=response.usage.completion_tokens,
            total_token_count=response.usage.total_tokens,
        )

    # Extract finish reason
    finish_reason = None
    if hasattr(response, "choices") and response.choices:
        choice = response.choices[0]
        if hasattr(choice, "finish_reason"):
            finish_reason = to_google_genai_finish_reason(choice.finish_reason)

    return LlmResponse(
        content=content, usage_metadata=usage_metadata, finish_reason=finish_reason
    )


class OpenAI(BaseLlm):
    """Integration with OpenAI GPT models.

    Attributes:
      model: The name of the OpenAI model.
      api_key: OpenAI API key (optional, can be set via environment variable).
      base_url: Custom base URL for OpenAI API (optional).
      max_tokens: Maximum number of tokens to generate.
      temperature: Sampling temperature (0.0 to 2.0).
      use_files_api: Whether to use OpenAI's Files API for file uploads (default: True).
    """

    model: str = "gpt-4o"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    use_files_api: bool = True

    @classmethod
    @override
    def supported_models(cls) -> list[str]:
        """Provides the list of supported models.

        Returns:
          A list of supported OpenAI model patterns.
        """
        return [
            r"gpt-.*",
            r"o1-.*",
            r"dall-e-.*",
            r"tts-.*",
            r"whisper-.*",
        ]

    @override
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        """Sends a request to the OpenAI model.

        Args:
          llm_request: LlmRequest, the request to send to the OpenAI model.
          stream: bool = False, whether to do streaming call.

        Yields:
          LlmResponse: The model response.
        """
        await self._preprocess_request(llm_request)
        self._maybe_append_user_content(llm_request)

        # Initialize OpenAI client
        client = self._get_openai_client()

        # Convert request to OpenAI format
        messages = []

        # Add system instruction if present
        if llm_request.config and llm_request.config.system_instruction:
            if isinstance(llm_request.config.system_instruction, str):
                messages.append(
                    {"role": "system", "content": llm_request.config.system_instruction}
                )

        # Convert contents to messages
        for content in llm_request.contents:
            message = await content_to_openai_message(content, self)
            messages.append(message)

        # Prepare tools if present
        tools = []
        if llm_request.config and llm_request.config.tools:
            for tool in llm_request.config.tools:
                if isinstance(tool, types.Tool) and tool.function_declarations:
                    for func_decl in tool.function_declarations:
                        openai_tool = function_declaration_to_openai_tool(func_decl)
                        tools.append(openai_tool)

        # Prepare request parameters
        request_params = {
            "model": llm_request.model or self.model,
            "messages": messages,
            "stream": stream,
        }

        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"

        if self.max_tokens:
            request_params["max_tokens"] = self.max_tokens
        elif llm_request.config and llm_request.config.max_output_tokens:
            request_params["max_tokens"] = llm_request.config.max_output_tokens

        if self.temperature is not None:
            request_params["temperature"] = self.temperature
        elif llm_request.config and llm_request.config.temperature is not None:
            request_params["temperature"] = llm_request.config.temperature

        logger.info(
            "Sending request to OpenAI, model: %s, stream: %s",
            request_params["model"],
            stream,
        )
        logger.debug(f"OpenAI request: {request_params}")

        try:
            if stream:
                # Handle streaming response
                stream_response = await client.chat.completions.create(**request_params)

                async for chunk in stream_response:
                    if chunk.choices:
                        choice = chunk.choices[0]
                        if choice.delta and choice.delta.content:
                            # Create partial response
                            partial_content = types.Content(
                                role="model",
                                parts=[types.Part(text=choice.delta.content)],
                            )
                            yield LlmResponse(
                                content=partial_content,
                                partial=True,
                                turn_complete=False,
                            )

                # Send final complete response
                yield LlmResponse(
                    content=types.Content(role="model", parts=[]), turn_complete=True
                )
            else:
                # Handle non-streaming response
                response = await client.chat.completions.create(**request_params)
                llm_response = openai_response_to_llm_response(response)
                yield llm_response

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            yield LlmResponse(error_code="OPENAI_API_ERROR", error_message=str(e))

    def _get_openai_client(self) -> openai.AsyncOpenAI:
        """Creates and returns an OpenAI client."""
        client_kwargs = {}

        # Set API key
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            client_kwargs["api_key"] = api_key

        # Set base URL if provided
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        return openai.AsyncOpenAI(**client_kwargs)

    async def _upload_file_to_openai(
        self, file_data: bytes, mime_type: str, display_name: Optional[str] = None
    ) -> str:
        """Upload a file to OpenAI's Files API and return the file ID."""
        if not self.use_files_api:
            raise ValueError(
                "Files API is disabled. Set use_files_api=True to enable file uploads."
            )

        client = self._get_openai_client()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=self._get_file_extension(mime_type)
        ) as temp_file:
            temp_file.write(file_data)
            temp_file_path = temp_file.name

        try:
            # Upload the file to OpenAI
            with open(temp_file_path, "rb") as f:
                uploaded_file = await client.files.create(
                    file=f,
                    purpose="assistants",  # Use assistants purpose for Chat Completions
                )

            logger.info(
                f"Uploaded file to OpenAI: {uploaded_file.id} ({display_name or 'unnamed'})"
            )
            return uploaded_file.id

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def _get_file_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        mime_to_ext = {
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "text/plain": ".txt",
            "text/markdown": ".md",
            "application/json": ".json",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        }
        return mime_to_ext.get(mime_type, ".bin")

    async def _handle_file_data(self, part: types.Part) -> Union[Dict[str, Any], str]:
        """Handle file data by uploading to OpenAI Files API or converting to base64."""
        if part.inline_data:
            # Handle inline data
            mime_type = part.inline_data.mime_type or "application/octet-stream"
            data = part.inline_data.data
            display_name = part.inline_data.display_name

            if self.use_files_api and mime_type in [
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ]:
                # Upload documents to Files API
                try:
                    file_id = await self._upload_file_to_openai(
                        data, mime_type, display_name
                    )
                    return {
                        "type": "text",
                        "text": f"[File uploaded to OpenAI: {display_name or 'unnamed file'} (ID: {file_id})]",
                    }
                except Exception as e:
                    logger.warning(
                        f"Failed to upload file to OpenAI Files API: {e}. Falling back to base64 encoding."
                    )

            # For images or when Files API is disabled, use base64 encoding
            if mime_type.startswith("image/"):
                data_b64 = base64.b64encode(data).decode()
                return {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{data_b64}"},
                }
            else:
                # For other file types, convert to base64 for vision models
                data_b64 = base64.b64encode(data).decode()
                return {
                    "type": "image_url",  # OpenAI treats documents as images for vision models
                    "image_url": {"url": f"data:{mime_type};base64,{data_b64}"},
                }

        elif part.file_data:
            # Handle file references (URIs)
            file_uri = part.file_data.file_uri or "unknown"
            display_name = part.file_data.display_name or "unnamed file"
            mime_type = part.file_data.mime_type or "unknown"

            logger.warning(
                f"OpenAI Chat API does not support file references. "
                f"File '{display_name}' ({file_uri}) converted to text description. "
                f"Consider uploading the file directly or using OpenAI's Files API."
            )

            return {
                "type": "text",
                "text": f"[FILE REFERENCE: {display_name}]\n"
                f"URI: {file_uri}\n"
                f"Type: {mime_type}\n"
                f"Note: OpenAI Chat API does not support file references. "
                f"Consider uploading the file directly or using OpenAI's Files API.",
            }

        return {"type": "text", "text": str(part)}

    async def _preprocess_request(self, llm_request: LlmRequest):
        """Preprocesses the request before sending to OpenAI."""
        # Set model if not specified
        if not llm_request.model:
            llm_request.model = self.model
