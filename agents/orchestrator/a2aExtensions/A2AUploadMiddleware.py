import base64, hashlib, uuid, time
import logging
from google.adk.artifacts import BaseArtifactService
from google.genai import types
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)

uploads = {}

class A2AUploadMiddleware(BaseHTTPMiddleware):
    """
    A2A Upload Middleware for handling file uploads via the A2A protocol.

    This middleware integrates with the BaseArtifactService to save uploaded files
    using the ADK Artifact Service. It supports both session-scoped and user-scoped
    artifacts with proper namespace handling.

    Features:
    - Chunked file upload support
    - SHA256 integrity verification
    - Session and user namespace support
    - Comprehensive error handling and logging
    - Integration with ArtifactData model
    """

    EXT_URI = "urn:orquestrator:artifact-upload:v1"
    APP_NAME = "orquestrator"
    METHODS = {
        "start": "artifactUpload/start",
        "append": "artifactUpload/append",
        "finish": "artifactUpload/finish",
        "abort": "artifactUpload/abort",
    }

    def __init__(self, app, artifact_service: BaseArtifactService):
        super().__init__(app)
        logger.info("Initializing A2AUploadMiddleware")
        self.artifact_service = artifact_service
        logger.info(f"Artifact service initialized: {type(self.artifact_service)}")
        logger.info(f"Artifact service details: {self.artifact_service.__dict__}")

    def cleanup_old_uploads(self, max_age_seconds: int = 3600):
        """Clean up old uploads to prevent memory leaks"""
        current_time = time.time()
        to_remove = []

        for upload_id, upload_data in uploads.items():
            if "created_at" in upload_data:
                if current_time - upload_data["created_at"] > max_age_seconds:
                    to_remove.append(upload_id)

        for upload_id in to_remove:
            uploads.pop(upload_id, None)
            logger.info(f"Cleaned up old upload: {upload_id}")

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old uploads")

    async def dispatch(self, request: Request, call_next):
        logger.info(f"A2A Upload Middleware: {request.method} {request.url.path}")
        logger.info(f"Headers: {dict(request.headers)}")

        if request.method == "POST" and request.url.path == "/":
            # Repare no header de negociação de extensões
            ext_hdr = request.headers.get("X-A2A-Extensions", "")
            logger.info(f"X-A2A-Extensions header: {ext_hdr}")
            logger.info(f"Looking for extension: {self.EXT_URI}")

            if self.EXT_URI in [s.strip() for s in ext_hdr.split(",")]:
                logger.info("Extension URI matched! Processing upload request")
                try:
                    payload = await request.json()
                except Exception:
                    return JSONResponse(
                        {
                            "jsonrpc": "2.0",
                            "error": {"code": -32700, "message": "Parse error"},
                            "id": None,
                        },
                        status_code=400,
                    )

                method = payload.get("method", "")
                req_id = payload.get("id")
                params = payload.get("params", {}) or {}

                if method == self.METHODS["start"]:
                    try:
                        filename = params["filename"]
                        mime = params.get("mimeType", "application/octet-stream")
                        sha256 = params.get("sha256")
                        user_id = params.get("userId")
                        session_id = params.get("sessionId", None)
                        upload_id = str(uuid.uuid4())
                        uploads[upload_id] = {
                            "buffer": bytearray(),
                            "filename": filename,
                            "mime": mime,
                            "sha256": sha256,
                            "userId": user_id,
                            "sessionId": session_id,
                            "created_at": time.time(),
                        }
                        logger.info(
                            f"Started upload: {filename} (upload_id: {upload_id})"
                        )
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "uploadId": upload_id,
                                    "maxChunkBytes": 524288,
                                },
                            }
                        )
                    except KeyError as e:
                        logger.error(f"Missing required parameter in start: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32602, "message": "Invalid params"},
                            },
                            status_code=400,
                        )
                    except Exception as e:
                        logger.error(f"Error in start method: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32603, "message": "Internal error"},
                            },
                            status_code=500,
                        )

                if method == self.METHODS["append"]:
                    try:
                        upload_id = params["uploadId"]
                        chunk_b64 = params["chunkBase64"]
                        offset = params.get("offset", 0)
                        up = uploads.get(upload_id)
                        if not up:
                            logger.warning(f"Invalid upload_id in append: {upload_id}")
                            return JSONResponse(
                                {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": {
                                        "code": -32004,
                                        "message": "uploadId inválido",
                                    },
                                },
                                status_code=400,
                            )
                        data = base64.b64decode(chunk_b64)
                        # checagem simples de offset
                        if offset != len(up["buffer"]):
                            logger.warning(
                                f"Offset mismatch for upload {upload_id}: expected {len(up['buffer'])}, got {offset}"
                            )
                            return JSONResponse(
                                {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": {
                                        "code": -32005,
                                        "message": "offset incorreto",
                                    },
                                },
                                status_code=409,
                            )
                        up["buffer"].extend(data)
                        logger.debug(
                            f"Appended {len(data)} bytes to upload {upload_id}, total: {len(up['buffer'])}"
                        )
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "received": len(data),
                                    "total": len(up["buffer"]),
                                },
                            }
                        )
                    except KeyError as e:
                        logger.error(f"Missing required parameter in append: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32602, "message": "Invalid params"},
                            },
                            status_code=400,
                        )
                    except Exception as e:
                        logger.error(f"Error in append method: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32603, "message": "Internal error"},
                            },
                            status_code=500,
                        )

                if method == self.METHODS["finish"]:
                    try:
                        upload_id = params["uploadId"]
                        up = uploads.pop(upload_id, None)
                        if not up:
                            logger.warning(f"Invalid upload_id in finish: {upload_id}")
                            return JSONResponse(
                                {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": {
                                        "code": -32004,
                                        "message": "uploadId inválido",
                                    },
                                },
                                status_code=400,
                            )

                        # integridade
                        if up["sha256"]:
                            h = hashlib.sha256(up["buffer"]).hexdigest()
                            if h != up["sha256"]:
                                logger.error(
                                    f"SHA256 mismatch for upload {upload_id}: expected {up['sha256']}, got {h}"
                                )
                                return JSONResponse(
                                    {
                                        "jsonrpc": "2.0",
                                        "id": req_id,
                                        "error": {
                                            "code": -32006,
                                            "message": "sha256 mismatch",
                                        },
                                    },
                                    status_code=400,
                                )

                        try:
                            # construir filename (suporta user: prefixo p/ namespace de utilizador)
                            filename = up.get("filename")
                            user_id = up.get("userId")
                            session_id = up.get("sessionId")
                            mime = up.get("mime")
                            buffer = up.get("buffer")
                            if not filename or not mime or not buffer:
                                raise ValueError(
                                    "Missing filename or mime type in upload data or even data itself"
                                )
                            namespace = None
                            if session_id is None:
                                namespace = "user"                    
                            else:
                                namespace = "session"


                            # Encode binary data to base64
                            base64_data = base64.b64encode(bytes(buffer)).decode(
                                "utf-8"
                            )

                            artifact = types.Part.from_bytes(
                                data=base64_data, mime_type=mime
                            )

                            logger.info(
                                f"Attempting to save artifact: {filename}, namespace: {namespace}, user_id: {user_id}, session_id: {session_id}"
                            )
                            logger.info(
                                f"Artifact data size: {len(base64_data)} chars (base64), {len(buffer)} bytes (binary)"
                            )

                            version = await self.artifact_service.save_artifact(
                                app_name=self.APP_NAME,
                                user_id=user_id,
                                session_id=session_id if namespace == "session" else None,
                                filename=filename,
                                artifact=artifact,
                            )
                            logger.info(
                                f"Saved artifact: {filename} (version: {version}) ({mime})"
                            )

                        except Exception as exc:
                            logger.error(
                                f"Error in finish artifact save: {exc}", exc_info=True
                            )
                            # Additional context logging if possible
                            logger.error(
                                f"Artifact service type: {type(self.artifact_service)}"
                            )
                            logger.error(
                                f"Artifact service details: {getattr(self.artifact_service, '__dict__', {})}"
                            )
                            return JSONResponse(
                                {
                                    "jsonrpc": "2.0",
                                    "id": req_id,
                                    "error": {
                                        "code": -32007,
                                        "message": "Failed to save artifact",
                                    },
                                },
                                status_code=500,
                            )

                        logger.info(
                            f"Successfully saved artifact: {filename} ({up['mime']}) - {len(up['buffer'])} bytes"
                        )

                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "filename": filename,
                                    "mimeType": up["mime"],
                                    "size": len(up["buffer"]),
                                    "namespace": namespace,
                                },
                            }
                        )
                    except KeyError as e:
                        logger.error(f"Missing required parameter in finish: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32602, "message": "Invalid params"},
                            },
                            status_code=400,
                        )
                    except Exception as e:
                        logger.error(f"Error in finish method: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32603, "message": "Internal error"},
                            },
                            status_code=500,
                        )

                if method == self.METHODS["abort"]:
                    try:
                        upload_id = params["uploadId"]
                        up = uploads.pop(upload_id, None)
                        if up:
                            logger.info(
                                f"Aborted upload: {up.get('filename', 'unknown')} (upload_id: {upload_id})"
                            )
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {"aborted": True},
                            }
                        )
                    except KeyError as e:
                        logger.error(f"Missing required parameter in abort: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32602, "message": "Invalid params"},
                            },
                            status_code=400,
                        )
                    except Exception as e:
                        logger.error(f"Error in abort method: {e}")
                        return JSONResponse(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32603, "message": "Internal error"},
                            },
                            status_code=500,
                        )

        # fora da extensão, deixe o A2A normal fluir
        logger.info("Extension URI not matched, passing to next middleware")
        return await call_next(request)
