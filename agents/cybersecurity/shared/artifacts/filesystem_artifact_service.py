"""An artifact service implementation using the local filesystem.

The file path format used depends on whether the filename has a user namespace:
  - For files with user namespace (starting with "user:"):
    {base_path}/{app_name}/{user_id}/user/{filename}/{version}
  - For regular session-scoped files:
    {base_path}/{app_name}/{user_id}/{session_id}/{filename}/{version}
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from google.genai import types
from typing_extensions import override

from google.adk.artifacts.base_artifact_service import BaseArtifactService

logger = logging.getLogger("google_adk." + __name__)


class FilesystemArtifactService(BaseArtifactService):
    """An artifact service implementation using the local filesystem."""

    def __init__(self, base_path: str = "./artifacts", **kwargs):
        """Initializes the FilesystemArtifactService.

        Args:
            base_path: The base directory path where artifacts will be stored.
            **kwargs: Additional keyword arguments (for compatibility).
        """
        self.base_path = Path(base_path).resolve()
        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"FilesystemArtifactService initialized with base_path: {self.base_path}")

    @override
    async def save_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        artifact: types.Part,
    ) -> int:
        return await asyncio.to_thread(
            self._save_artifact,
            app_name,
            user_id,
            session_id,
            filename,
            artifact,
        )

    @override
    async def load_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        return await asyncio.to_thread(
            self._load_artifact,
            app_name,
            user_id,
            session_id,
            filename,
            version,
        )

    @override
    async def list_artifact_keys(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> list[str]:
        return await asyncio.to_thread(
            self._list_artifact_keys,
            app_name,
            user_id,
            session_id,
        )

    @override
    async def delete_artifact(
        self, *, app_name: str, user_id: str, session_id: str, filename: str
    ) -> None:
        return await asyncio.to_thread(
            self._delete_artifact,
            app_name,
            user_id,
            session_id,
            filename,
        )

    @override
    async def list_versions(
        self, *, app_name: str, user_id: str, session_id: str, filename: str
    ) -> list[int]:
        return await asyncio.to_thread(
            self._list_versions,
            app_name,
            user_id,
            session_id,
            filename,
        )

    def _file_has_user_namespace(self, filename: str) -> bool:
        """Checks if the filename has a user namespace.

        Args:
            filename: The filename to check.

        Returns:
            True if the filename has a user namespace (starts with "user:"),
            False otherwise.
        """
        return filename.startswith("user:")

    def _get_file_path(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        version: int | str,
    ) -> Path:
        """Constructs the file path on the filesystem.

        Args:
            app_name: The name of the application.
            user_id: The ID of the user.
            session_id: The ID of the session.
            filename: The name of the artifact file.
            version: The version of the artifact.

        Returns:
            The constructed file path.
        """
        if self._file_has_user_namespace(filename):
            return self.base_path / app_name / user_id / "user" / filename / str(version)
        return self.base_path / app_name / user_id / session_id / filename / str(version)

    def _save_artifact(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        artifact: types.Part,
    ) -> int:
        versions = self._list_versions(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
        )
        version = 0 if not versions else max(versions) + 1

        file_path = self._get_file_path(
            app_name, user_id, session_id, filename, version
        )
        
        # Create directory structure
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if artifact.inline_data:
                # Save binary data
                with open(file_path, "wb") as f:
                    f.write(artifact.inline_data.data)
                
                # Save metadata (mime type) in a separate file
                metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
                with open(metadata_path, "w", encoding="utf-8") as f:
                    f.write(artifact.inline_data.mime_type)
                    
            elif artifact.text:
                # Save text data
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(artifact.text)
                    
                # Save metadata indicating this is text
                metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
                with open(metadata_path, "w", encoding="utf-8") as f:
                    f.write("text/plain")
            else:
                raise ValueError("Artifact must have either inline_data or text.")

            logger.info(f"Saved artifact: {file_path}")
            return version
            
        except Exception as e:
            logger.error(f"Failed to save artifact to {file_path}: {e}")
            # Clean up partial files
            if file_path.exists():
                file_path.unlink()
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            if metadata_path.exists():
                metadata_path.unlink()
            raise

    def _load_artifact(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        filename: str,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        if version is None:
            versions = self._list_versions(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
            )
            if not versions:
                return None
            version = max(versions)

        file_path = self._get_file_path(
            app_name, user_id, session_id, filename, version
        )
        
        if not file_path.exists():
            return None

        try:
            # Load metadata to determine content type
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            mime_type = "application/octet-stream"  # default
            
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    mime_type = f.read().strip()

            # Load the artifact based on mime type
            if mime_type == "text/plain":
                # Load as text
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
                return types.Part(text=text_content)
            else:
                # Load as binary data
                with open(file_path, "rb") as f:
                    binary_data = f.read()
                return types.Part.from_bytes(data=binary_data, mime_type=mime_type)
                
        except Exception as e:
            logger.error(f"Failed to load artifact from {file_path}: {e}")
            return None

    def _list_artifact_keys(
        self, app_name: str, user_id: str, session_id: str
    ) -> list[str]:
        filenames = set()

        # List session-scoped artifacts
        session_path = self.base_path / app_name / user_id / session_id
        if session_path.exists():
            for item in session_path.iterdir():
                if item.is_dir():
                    filenames.add(item.name)

        # List user-scoped artifacts
        user_path = self.base_path / app_name / user_id / "user"
        if user_path.exists():
            for item in user_path.iterdir():
                if item.is_dir():
                    filenames.add(item.name)

        return sorted(list(filenames))

    def _delete_artifact(
        self, app_name: str, user_id: str, session_id: str, filename: str
    ) -> None:
        versions = self._list_versions(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename,
        )
        
        for version in versions:
            file_path = self._get_file_path(
                app_name, user_id, session_id, filename, version
            )
            
            try:
                # Delete the artifact file
                if file_path.exists():
                    file_path.unlink()
                    
                # Delete the metadata file
                metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
                if metadata_path.exists():
                    metadata_path.unlink()
                    
                logger.info(f"Deleted artifact: {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to delete artifact {file_path}: {e}")

        # Clean up empty directories
        try:
            artifact_dir = self._get_file_path(app_name, user_id, session_id, filename, "").parent
            if artifact_dir.exists() and not any(artifact_dir.iterdir()):
                artifact_dir.rmdir()
                logger.info(f"Removed empty artifact directory: {artifact_dir}")
        except Exception as e:
            logger.debug(f"Could not remove directory {artifact_dir}: {e}")

    def _list_versions(
        self, app_name: str, user_id: str, session_id: str, filename: str
    ) -> list[int]:
        """Lists all available versions of an artifact.

        This method retrieves all versions of a specific artifact by scanning
        the filesystem directory structure.

        Args:
            app_name: The name of the application.
            user_id: The ID of the user who owns the artifact.
            session_id: The ID of the session (ignored for user-namespaced files).
            filename: The name of the artifact file.

        Returns:
            A list of version numbers (integers) available for the specified artifact.
            Returns an empty list if no versions are found.
        """
        # Get the artifact directory (where version files are stored)
        # This should be: {base_path}/{app_name}/{user_id}/{session_id}/{filename}/
        file_path = self._get_file_path(app_name, user_id, session_id, filename, "")
        
        # The artifact directory is the parent of the file path
        # But we need to handle the case where _get_file_path returns the directory itself
        if file_path.name == filename:
            # _get_file_path returned the artifact directory
            artifact_dir = file_path
        else:
            # _get_file_path returned a file path, so we need the parent
            artifact_dir = file_path.parent
        
        if not artifact_dir.exists():
            return []

        versions = []
        try:
            for item in artifact_dir.iterdir():
                if item.is_file() and not item.name.endswith(".meta"):
                    try:
                        version = int(item.name)
                        versions.append(version)
                    except ValueError:
                        # Skip non-numeric version names
                        continue
                elif item.is_dir():
                    try:
                        version = int(item.name)
                        versions.append(version)
                    except ValueError:
                        # Skip non-numeric directory names
                        continue
        except Exception as e:
            logger.error(f"Error listing versions in {artifact_dir}: {e}")
            
        return sorted(versions)
