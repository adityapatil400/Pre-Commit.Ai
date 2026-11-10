import io
import json
import os
import shutil
import time
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.app.config import settings
from backend.app.schemas.project_schema import ProjectResponse
from backend.app.utils.logger import logger
from backend.app.utils.security import SecurityValidator

class WorkspaceServiceError(Exception):
    """Base exception for workspace management failures."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class InvalidFileInputError(WorkspaceServiceError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class ProjectNotFoundError(WorkspaceServiceError):
    def __init__(self, project_id: str):
        super().__init__(f"Project '{project_id}' not found or workspace has expired.", status_code=404)

class WorkspaceService:
    """
    Manages isolated temporary project workspaces on disk.
    Enforces security validations (Zip-Slip prevention, decompression limits),
    filters excluded directories, preserves relative file paths, and tracks metadata.
    """

    # In-memory registry for fast lookup: project_id -> ProjectResponse
    _PROJECT_REGISTRY: Dict[str, ProjectResponse] = {}

    @classmethod
    def get_workspace_path(cls, project_id: str) -> Path:
        """Returns the isolated workspace directory path for a given project ID."""
        return Path(settings.workspaces_dir) / project_id

    @classmethod
    def get_project(cls, project_id: str) -> ProjectResponse:
        """
        Retrieves project metadata by project_id.
        Checks memory registry first, then recovers from on-disk project.json if workspace exists.
        """
        if project_id in cls._PROJECT_REGISTRY:
            return cls._PROJECT_REGISTRY[project_id]

        workspace_dir = cls.get_workspace_path(project_id)
        metadata_file = workspace_dir / "project.json"

        if workspace_dir.exists() and metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    project = ProjectResponse(**data)
                    cls._PROJECT_REGISTRY[project_id] = project
                    return project
            except Exception as e:
                logger.error(f"Failed to read project metadata from disk for {project_id}: {e}")

        raise ProjectNotFoundError(project_id)

    @classmethod
    def list_projects(cls) -> List[ProjectResponse]:
        """Lists all registered active projects."""
        return list(cls._PROJECT_REGISTRY.values())

    @classmethod
    def cleanup_workspace(cls, project_id: str) -> bool:
        """
        Safely removes an isolated temporary workspace directory and unregisters the project.
        """
        workspace_dir = cls.get_workspace_path(project_id)
        removed = False

        if workspace_dir.exists():
            try:
                shutil.rmtree(workspace_dir, ignore_errors=True)
                removed = True
                logger.info(f"Cleaned up workspace directory: {workspace_dir}")
            except Exception as e:
                logger.error(f"Error deleting workspace {workspace_dir}: {e}")

        if project_id in cls._PROJECT_REGISTRY:
            del cls._PROJECT_REGISTRY[project_id]
            removed = True

        return removed

    @classmethod
    def cleanup_expired_workspaces(cls, max_age_hours: Optional[int] = None) -> int:
        """
        Removes temporary workspaces that have exceeded the expiry duration.
        """
        max_age = (max_age_hours or settings.WORKSPACE_EXPIRY_HOURS) * 3600
        now = time.time()
        cleaned_count = 0

        workspaces_root = Path(settings.workspaces_dir)
        if not workspaces_root.exists():
            return 0

        for item in workspaces_root.iterdir():
            if item.is_dir():
                mtime = item.stat().st_mtime
                if now - mtime > max_age:
                    project_id = item.name
                    cls.cleanup_workspace(project_id)
                    cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired workspaces.")
        return cleaned_count

    @classmethod
    def save_project(cls, project: ProjectResponse) -> None:
        """Saves project metadata to in-memory registry and disk project.json."""
        workspace_dir = cls.get_workspace_path(project.project_id)
        cls._save_project_metadata(project, workspace_dir)

    @classmethod
    def _save_project_metadata(cls, project: ProjectResponse, workspace_dir: Path) -> None:
        """Saves project metadata to in-memory registry and disk project.json."""
        cls._PROJECT_REGISTRY[project.project_id] = project
        metadata_file = workspace_dir / "project.json"
        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(project.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write project.json in {workspace_dir}: {e}")

    @classmethod
    def create_workspace_from_single_file(
        cls,
        filename: str,
        content_bytes: bytes,
        project_name: Optional[str] = None
    ) -> ProjectResponse:
        """
        Stores an individual .py file in a new isolated workspace.
        """
        if not filename.endswith(".py"):
            raise InvalidFileInputError("File must have a .py extension.")

        # Check file size limit
        if len(content_bytes) > settings.max_file_size_bytes:
            raise InvalidFileInputError(
                f"File size exceeds maximum allowed size ({settings.MAX_FILE_SIZE_MB}MB)."
            )

        # Validate file content: verify it is decodable text and not binary executable
        if b"\x00" in content_bytes[:1024]:
            raise InvalidFileInputError("Invalid Python file content. Binary or non-text content detected.")

        try:
            content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content_bytes.decode("latin-1")
            except Exception:
                raise InvalidFileInputError("Unable to decode Python source code. Must be UTF-8 or Latin-1 text.")

        # Assign unique analysis ID
        project_id = str(uuid.uuid4())
        workspace_dir = cls.get_workspace_path(project_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Clean sanitized filename
        clean_filename = os.path.basename(filename)
        dest_path = workspace_dir / clean_filename

        try:
            with open(dest_path, "wb") as f:
                f.write(content_bytes)
        except Exception as e:
            shutil.rmtree(workspace_dir, ignore_errors=True)
            raise WorkspaceServiceError(f"Failed to write file to workspace: {str(e)}")

        p_name = project_name or clean_filename.replace(".py", "")

        project = ProjectResponse(
            project_id=project_id,
            project_name=p_name,
            input_type="file",
            source_repository=None,
            branch=None,
            base_commit_sha=None,
            python_files=[clean_filename],
            total_files=1,
        )

        cls._save_project_metadata(project, workspace_dir)
        logger.info(f"Created single-file workspace: {project_id} ({clean_filename})")
        return project

    @classmethod
    def create_workspace_from_zip(
        cls,
        filename: str,
        zip_bytes: bytes,
        project_name: Optional[str] = None,
        strip_single_root: bool = True,
        input_type: str = "zip",
        source_repository: Optional[str] = None,
        branch: Optional[str] = None,
        base_commit_sha: Optional[str] = None,
    ) -> ProjectResponse:
        """
        Safely unpacks a ZIP archive into an isolated workspace directory.
        Applies Zip-Slip protection, ignores cache/virtualenv dirs, and discovers all Python files recursively.
        """
        # Validate archive size
        if len(zip_bytes) > settings.max_upload_size_bytes:
            raise InvalidFileInputError(
                f"ZIP archive size ({len(zip_bytes) // (1024*1024)}MB) exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # Validate ZIP format
        try:
            zip_buffer = io.BytesIO(zip_bytes)
            if not zipfile.is_zipfile(zip_buffer):
                raise InvalidFileInputError("The uploaded file is not a valid ZIP archive.")
            zip_file = zipfile.ZipFile(zip_buffer)
        except (zipfile.BadZipFile, Exception) as e:
            raise InvalidFileInputError(f"Failed to read ZIP archive: {str(e)}")

        project_id = str(uuid.uuid4())
        workspace_dir = cls.get_workspace_path(project_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        try:
            names = zip_file.namelist()
            total_uncompressed_size = 0
            extracted_count = 0

            # Determine if archive has a single top-level directory (e.g. GitHub archive prefix or folder zip)
            root_prefix = ""
            if strip_single_root and names:
                first_parts = [n.split("/")[0] for n in names if n.strip("/") and not n.startswith(".")]
                if first_parts and all(p == first_parts[0] for p in first_parts):
                    root_prefix = first_parts[0] + "/"

            for member_name in names:
                # 1. Zip-Slip check: verify normalized path
                norm = os.path.normpath(member_name)
                if norm.startswith("..") or os.path.isabs(norm) or norm.startswith("/") or norm.startswith("\\"):
                    logger.warning(f"Blocked Zip-Slip path attempt: {member_name}")
                    continue

                # Strip root prefix if detected
                rel_name = member_name
                if root_prefix and rel_name.startswith(root_prefix):
                    rel_name = rel_name[len(root_prefix):]

                rel_name = os.path.normpath(rel_name)
                if not rel_name or rel_name == ".":
                    continue

                # 2. Ignore unnecessary directories (.git, __pycache__, .venv, etc.)
                parts = rel_name.split(os.sep)
                if any(p in settings.IGNORED_DIRS or p.startswith(".") for p in parts):
                    continue

                info = zip_file.getinfo(member_name)
                if info.is_dir():
                    continue

                total_uncompressed_size += info.file_size
                if total_uncompressed_size > settings.max_upload_size_bytes:
                    raise InvalidFileInputError(
                        f"Uncompressed archive contents exceed size limit ({settings.MAX_UPLOAD_SIZE_MB}MB)."
                    )

                extracted_count += 1
                if extracted_count > settings.MAX_PROJECT_FILES:
                    raise InvalidFileInputError(
                        f"Archive exceeds maximum allowed file count ({settings.MAX_PROJECT_FILES} files)."
                    )

                # 3. Path Traversal Boundary check against destination workspace directory
                target_file_path = (workspace_dir / rel_name).resolve()
                if not str(target_file_path).startswith(str(workspace_dir.resolve())):
                    logger.warning(f"Prevented directory escape: {rel_name}")
                    continue

                target_file_path.parent.mkdir(parents=True, exist_ok=True)

                with zip_file.open(member_name) as source, open(target_file_path, "wb") as dest:
                    shutil.copyfileobj(source, dest)

            # Discover all Python files recursively
            discovered_python_files: List[str] = []
            for path in workspace_dir.rglob("*.py"):
                if path.is_file():
                    # Double-check that it does not reside in an ignored dir
                    rel = path.relative_to(workspace_dir).as_posix()
                    parts = rel.split("/")
                    if not any(p in settings.IGNORED_DIRS or p.startswith(".") for p in parts):
                        discovered_python_files.append(rel)

            discovered_python_files.sort()

            if not discovered_python_files:
                raise InvalidFileInputError("No Python (.py) source files found in the archive.")

            p_name = project_name
            if not p_name:
                p_name = filename.replace(".zip", "") if filename.endswith(".zip") else "python-project"

            project = ProjectResponse(
                project_id=project_id,
                project_name=p_name,
                input_type=input_type,
                source_repository=source_repository,
                branch=branch,
                base_commit_sha=base_commit_sha,
                python_files=discovered_python_files,
                total_files=len(discovered_python_files),
            )

            cls._save_project_metadata(project, workspace_dir)
            logger.info(
                f"Successfully extracted {len(discovered_python_files)} Python files into workspace {project_id}"
            )
            return project

        except Exception as e:
            # Clean up on failure
            shutil.rmtree(workspace_dir, ignore_errors=True)
            if isinstance(e, WorkspaceServiceError):
                raise
            raise WorkspaceServiceError(f"Failed to process archive: {str(e)}")

