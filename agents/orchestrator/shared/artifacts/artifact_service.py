"""
ADK Artifact Service wrapper for file handling
"""

import os
import base64
import logging
from typing import Optional, List, Dict, Any

# Google ADK SDK imports
from google.adk.artifacts import InMemoryArtifactService, GcsArtifactService
from google.genai.types import Part, Blob

from pydantic import BaseModel
from .filesystem_artifact_service import FilesystemArtifactService

logger = logging.getLogger(__name__)

class ArtifactData(BaseModel):
    """Artifact data model for A2A protocol"""
    filename: str
    mime_type: str
    data: str  # Base64 encoded binary data
    version: Optional[int] = None
    namespace: Optional[str] = None  # "user:" prefix for user-scoped artifacts


class ArtifactServiceWrapper:
    """Wrapper for ADK Artifact Service with A2A protocol support"""
    
    def __init__(self, service_type: str = "in_memory", **kwargs):
        self.service_type = service_type
        self.artifact_service = self._create_service(service_type, **kwargs)
        
    def _create_service(self, service_type: str, **kwargs):
        """Create appropriate artifact service"""
        try:
            logger.info(f"Creating artifact service of type: {service_type}")
            if service_type == "in_memory":
                service = InMemoryArtifactService()
                logger.info(f"Created InMemoryArtifactService: {type(service)}")
                return service
            elif service_type == "gcs":
                bucket_name = kwargs.get('bucket_name', os.getenv('GCS_ARTIFACT_BUCKET'))
                if not bucket_name:
                    raise ValueError("GCS bucket name required for GcsArtifactService")
                service = GcsArtifactService(bucket_name=bucket_name)
                logger.info(f"Created GcsArtifactService: {type(service)}")
                return service
            elif service_type == "filesystem":
                base_path = kwargs.get('base_path', os.getenv('FILESYSTEM_ARTIFACT_PATH', './artifacts'))
                service = FilesystemArtifactService(base_path=base_path)
                logger.info(f"Created FilesystemArtifactService: {type(service)} at {base_path}")
                return service
            else:
                raise ValueError(f"Unsupported artifact service type: {service_type}")
        except Exception as e:
            logger.error(f"Failed to create artifact service: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fallback to in-memory service
            logger.warning("Falling back to InMemoryArtifactService")
            try:
                service = InMemoryArtifactService()
                logger.info(f"Fallback service created: {type(service)}")
                return service
            except Exception as fallback_error:
                logger.error(f"Even fallback service creation failed: {fallback_error}")
                raise
    
    async def save_artifact_from_data(self, artifact_data: ArtifactData, session_id: str) -> bool:
        """Save artifact from ArtifactData model"""
        try:
            # Decode base64 data
            binary_data = base64.b64decode(artifact_data.data)
            
            # Create Part object
            part = Part(
                inline_data=Blob(
                    mime_type=artifact_data.mime_type,
                    data=binary_data
                )
            )
            
            # Extract app_name, user_id from namespace or use defaults
            app_name = "agent-platform"  # Default app name
            user_id = "default-user"     # Default user ID
            
            # Handle namespace - if it contains user: prefix, extract filename
            filename = artifact_data.filename
            if artifact_data.namespace and artifact_data.namespace.startswith("user"):
                filename = f"user:{artifact_data.filename}"
            
            # Save artifact using correct ADK method signature
            version = await self.artifact_service.save_artifact(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                artifact=part
            )
            
            logger.info(f"Saved artifact: {filename} (version: {version}) ({artifact_data.mime_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception args: {e.args}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def load_artifact_to_data(self, filename: str, session_id: str, version: Optional[int] = None) -> Optional[ArtifactData]:
        """Load artifact to ArtifactData model"""
        try:
            # Extract app_name, user_id (same as save method)
            app_name = "agent-platform"
            user_id = "default-user"
            
            # Handle user: prefix in filename
            actual_filename = filename
            if filename.startswith("user:"):
                # Keep the user: prefix for ADK
                actual_filename = filename
            
            # Load artifact using correct ADK method signature
            part = await self.artifact_service.load_artifact(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=actual_filename,
                version=version
            )
            
            if not part or not part.inline_data:
                return None
            
            # Encode to base64
            binary_data = part.inline_data.data
            base64_data = base64.b64encode(binary_data).decode('utf-8')
            
            # Determine namespace for return
            namespace = "user" if filename.startswith("user:") else f"session:{session_id}"
            
            return ArtifactData(
                filename=actual_filename,
                mime_type=part.inline_data.mime_type,
                data=base64_data,
                version=version,
                namespace=namespace
            )
            
        except Exception as e:
            logger.error(f"Failed to load artifact: {e}")
            return None
    
    def list_artifacts(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available artifacts"""
        try:
            artifacts = []
            
            # List session artifacts
            session_namespace = f"session:{session_id}"
            session_files = self.artifact_service.list_artifacts(session_namespace)
            for filename in session_files:
                artifacts.append({
                    "filename": filename,
                    "namespace": "session",
                    "session_id": session_id
                })
            
            # List user artifacts if user_id provided
            if user_id:
                user_namespace = "user"
                user_files = self.artifact_service.list_artifacts(user_namespace)
                for filename in user_files:
                    artifacts.append({
                        "filename": filename,
                        "namespace": "user",
                        "user_id": user_id
                    })
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to list artifacts: {e}")
            return []
    
    def delete_artifact(self, filename: str, session_id: str) -> bool:
        """Delete artifact"""
        try:
            # Determine namespace
            if filename.startswith("user:"):
                namespace = "user"
                actual_filename = filename[5:]
            else:
                namespace = f"session:{session_id}"
                actual_filename = filename
            
            full_filename = f"{namespace}/{actual_filename}"
            
            # Delete artifact
            self.artifact_service.delete_artifact(full_filename)
            
            logger.info(f"Deleted artifact: {full_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete artifact: {e}")
            return False


def create_artifact_service() -> ArtifactServiceWrapper:
    """Create artifact service based on environment configuration"""
    service_type = os.getenv('ARTIFACT_SERVICE_TYPE', 'in_memory')
    
    kwargs = {}
    if service_type == 'gcs':
        kwargs['bucket_name'] = os.getenv('GCS_ARTIFACT_BUCKET')
    elif service_type == 'filesystem':
        kwargs['base_path'] = os.getenv('FILESYSTEM_ARTIFACT_PATH', './artifacts')
    
    return ArtifactServiceWrapper(service_type=service_type, **kwargs)
