"""
ADK Artifact Service wrapper for file handling
"""

import os
import base64
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# Google ADK SDK imports
from google.adk.artifacts import InMemoryArtifactService, GcsArtifactService
from google.genai.types import Part, Blob

from models import ArtifactData

logger = logging.getLogger(__name__)


class ArtifactServiceWrapper:
    """Wrapper for ADK Artifact Service with A2A protocol support"""
    
    def __init__(self, service_type: str = "in_memory", **kwargs):
        self.service_type = service_type
        self.artifact_service = self._create_service(service_type, **kwargs)
        
    def _create_service(self, service_type: str, **kwargs):
        """Create appropriate artifact service"""
        try:
            if service_type == "in_memory":
                return InMemoryArtifactService()
            elif service_type == "gcs":
                bucket_name = kwargs.get('bucket_name', os.getenv('GCS_ARTIFACT_BUCKET'))
                if not bucket_name:
                    raise ValueError("GCS bucket name required for GcsArtifactService")
                return GcsArtifactService(bucket_name=bucket_name)
            else:
                raise ValueError(f"Unsupported artifact service type: {service_type}")
        except Exception as e:
            logger.error(f"Failed to create artifact service: {e}")
            # Fallback to in-memory service
            logger.warning("Falling back to InMemoryArtifactService")
            return InMemoryArtifactService()
    
    def save_artifact_from_data(self, artifact_data: ArtifactData, session_id: str) -> bool:
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
            
            # Determine namespace
            namespace = artifact_data.namespace or f"session:{session_id}"
            filename = f"{namespace}/{artifact_data.filename}"
            
            # Save artifact
            self.artifact_service.save_artifact(
                filename=filename,
                part=part
            )
            
            logger.info(f"Saved artifact: {filename} ({artifact_data.mime_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")
            return False
    
    def load_artifact_to_data(self, filename: str, session_id: str, version: Optional[int] = None) -> Optional[ArtifactData]:
        """Load artifact to ArtifactData model"""
        try:
            # Determine namespace
            if filename.startswith("user:"):
                namespace = "user"
                actual_filename = filename[5:]  # Remove "user:" prefix
            else:
                namespace = f"session:{session_id}"
                actual_filename = filename
            
            full_filename = f"{namespace}/{actual_filename}"
            
            # Load artifact
            part = self.artifact_service.load_artifact(
                filename=full_filename,
                version=version
            )
            
            if not part or not part.inline_data:
                return None
            
            # Encode to base64
            binary_data = part.inline_data.data
            base64_data = base64.b64encode(binary_data).decode('utf-8')
            
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
    
    return ArtifactServiceWrapper(service_type=service_type, **kwargs)
