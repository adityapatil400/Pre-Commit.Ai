import io
import os
import re
import zipfile
import tempfile
import pathlib
from typing import Dict, Tuple, Optional
import httpx

GITHUB_REPO_REGEX = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$")

class SourceRetrievalError(Exception):
    pass

class SourceRetriever:
    """
    Handles secure source code retrieval for:
    1. Single Python file uploads (.py)
    2. Compressed ZIP projects (.zip)
    3. Public or private GitHub repositories
    """

    @staticmethod
    def from_single_file(filename: str, content_bytes: bytes) -> Dict[str, str]:
        """Extract a single Python file."""
        if not filename.endswith(".py"):
            filename = f"{filename}.py"
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = content_bytes.decode("latin-1")
        return {filename: text}

    @staticmethod
    def from_zip_bytes(zip_bytes: bytes, max_files: int = 1000, max_total_size: int = 50 * 1024 * 1024) -> Dict[str, str]:
        """
        Safely extracts Python files from in-memory ZIP archive.
        Guards against Zip Slip (path traversal) and decompression bombs.
        """
        python_files: Dict[str, str] = {}
        total_extracted_size = 0

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                # Find common root prefix if archive contains an enclosing folder
                names = z.namelist()
                for name in names:
                    # Security checks: prevent path traversal (Zip-Slip)
                    normalized = os.path.normpath(name)
                    if normalized.startswith("..") or os.path.isabs(normalized):
                        continue

                    # Filter out non-python, hidden, and build directories
                    if not normalized.endswith(".py"):
                        continue
                    if any(part.startswith(".") or part in ("__pycache__", "venv", ".venv", "env", "node_modules", "build", "dist") for part in normalized.split(os.sep)):
                        continue

                    info = z.getinfo(name)
                    if info.is_dir():
                        continue

                    total_extracted_size += info.file_size
                    if total_extracted_size > max_total_size:
                        raise SourceRetrievalError("ZIP archive exceeds max allowed uncompressed size (50MB).")

                    if len(python_files) >= max_files:
                        break

                    with z.open(name) as f:
                        raw = f.read()
                        try:
                            decoded = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            decoded = raw.decode("latin-1")
                        
                        # Clean prefix if single root folder exists
                        clean_name = normalized
                        parts = clean_name.split(os.sep)
                        if len(parts) > 1 and not parts[0].endswith(".py"):
                            clean_name = os.path.join(*parts[1:])

                        python_files[clean_name] = decoded
        except zipfile.BadZipFile:
            raise SourceRetrievalError("The uploaded file is not a valid or readable ZIP archive.")

        if not python_files:
            raise SourceRetrievalError("No Python (.py) source files found in the uploaded archive.")

        return python_files

    @classmethod
    async def from_github(cls, repo_url: str, token: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
        """
        Securely retrieves Python source files from GitHub via GitHub archive zipball.
        Returns (project_name, Dict[file_path, content]).
        """
        match = GITHUB_REPO_REGEX.match(repo_url.strip())
        if not match:
            raise SourceRetrievalError("Invalid GitHub repository URL. Format must be https://github.com/owner/repo")

        owner, repo = match.group(1), match.group(2)
        repo = repo.replace(".git", "")
        project_name = f"{owner}/{repo}"

        zipball_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PreCommit-AI-AST-Scanner"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(follow_redirects=True, timeout=25.0) as client:
            resp = await client.get(zipball_url, headers=headers)
            if resp.status_code == 404:
                raise SourceRetrievalError(f"GitHub repository `{project_name}` not found. Ensure it is public or provide an authorization token.")
            elif resp.status_code == 401 or resp.status_code == 403:
                msg = resp.json().get("message", "API rate limit exceeded or access denied")
                raise SourceRetrievalError(f"GitHub API Error: {msg}")
            elif resp.status_code != 200:
                raise SourceRetrievalError(f"Failed to fetch repository from GitHub (HTTP {resp.status_code}).")

            files = cls.from_zip_bytes(resp.content)
            return project_name, files

