import io
import os
import zipfile
from typing import Dict, Optional, Tuple
from backend.app.config import Settings
from backend.app.utils.logger import logger
from backend.app.utils.security import SecurityValidator

settings = Settings()

class FileServiceError(Exception):
    """Custom exception raised for file processing failures."""
    pass

class FileService:
    """
    Manages safe file extraction, archive extraction, and ZIP repackaging.
    Enforces security boundaries (Zip-Slip prevention, decompression bomb checks).
    """

    # In-memory session cache: session_id -> session data
    _ACTIVE_SESSIONS: Dict[str, dict] = {}

    @classmethod
    def save_session(cls, session_id: str, data: dict) -> None:
        cls._ACTIVE_SESSIONS[session_id] = data
        logger.info(f"Session saved: {session_id} (Project: {data.get('project_name')})")

    @classmethod
    def get_session(cls, session_id: str) -> Optional[dict]:
        return cls._ACTIVE_SESSIONS.get(session_id)

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        if session_id in cls._ACTIVE_SESSIONS:
            del cls._ACTIVE_SESSIONS[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False

    @classmethod
    def list_sessions(cls) -> Dict[str, dict]:
        return cls._ACTIVE_SESSIONS

    @staticmethod
    def extract_single_python_file(filename: str, content_bytes: bytes) -> Dict[str, str]:
        """
        Safely reads a single Python source file into memory.
        """
        if not filename.endswith(".py"):
            filename = f"{filename}.py"

        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content_bytes.decode("latin-1")
            except Exception as e:
                raise FileServiceError(f"Failed to decode Python file `{filename}`: {str(e)}")

        logger.debug(f"Extracted single file: {filename} ({len(text.splitlines())} lines)")
        return {filename: text}

    @staticmethod
    def extract_zip_archive(
        zip_bytes: bytes,
        max_files: int = 1000,
        max_total_size: int = settings.max_upload_size_bytes
    ) -> Dict[str, str]:
        """
        Safely unpacks Python files from an in-memory ZIP archive.
        Protects against Zip-Slip path traversals and zip-bomb resource exhaustion.
        """
        python_files: Dict[str, str] = {}
        total_extracted_size = 0

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                names = z.namelist()
                for name in names:
                    # Guard against Zip-Slip path traversal
                    if not SecurityValidator.is_safe_path(name):
                        logger.warning(f"Skipping potentially malicious path in ZIP: {name}")
                        continue

                    # Filter only python files
                    normalized = os.path.normpath(name)
                    if not normalized.endswith(".py"):
                        continue

                    # Filter out hidden files, venv, and cache folders
                    parts = normalized.split(os.sep)
                    if any(part.startswith(".") or part in ("__pycache__", "venv", ".venv", "env", "node_modules", "build", "dist") for part in parts):
                        continue

                    info = z.getinfo(name)
                    if info.is_dir():
                        continue

                    total_extracted_size += info.file_size
                    if total_extracted_size > max_total_size:
                        raise FileServiceError(f"ZIP archive exceeds max allowed uncompressed size ({settings.MAX_UPLOAD_SIZE_MB}MB).")

                    if len(python_files) >= max_files:
                        logger.warning(f"Reached max file extraction limit ({max_files})")
                        break

                    with z.open(name) as f:
                        raw = f.read()
                        try:
                            decoded = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            decoded = raw.decode("latin-1")

                        # Strip top-level wrapper directory if present
                        clean_name = normalized
                        if len(parts) > 1 and not parts[0].endswith(".py"):
                            clean_name = os.path.join(*parts[1:])

                        python_files[clean_name] = decoded

        except zipfile.BadZipFile:
            raise FileServiceError("Uploaded file is not a valid or readable ZIP archive.")

        if not python_files:
            raise FileServiceError("No Python (.py) source files found in the archive.")

        logger.info(f"Extracted {len(python_files)} Python files ({total_extracted_size} bytes)")
        return python_files

    @staticmethod
    def create_patched_zip(files_content: Dict[str, str]) -> io.BytesIO:
        """
        Packs modified/patched files into a new in-memory ZIP buffer.
        """
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for file_path, content in files_content.items():
                z.writestr(file_path, content)

        zip_buffer.seek(0)
        return zip_buffer

