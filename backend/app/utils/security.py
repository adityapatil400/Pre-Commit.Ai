import os
import re
from typing import Optional

class SecurityValidator:
    """
    Security helpers for sanitizing file paths, preventing Zip-Slip,
    and handling sensitive API tokens.
    """

    GITHUB_REPO_REGEX = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$")

    # Common patterns for API keys, tokens, and secrets
    SECRET_PATTERNS = [
        re.compile(r"(ghp_[a-zA-Z0-9]{20,})", re.IGNORECASE),
        re.compile(r"(github_pat_[a-zA-Z0-9_]{20,})", re.IGNORECASE),
        re.compile(r"(sk-[a-zA-Z0-9]{20,})", re.IGNORECASE),
        re.compile(r"(bearer\s+[a-zA-Z0-9._\-]{20,})", re.IGNORECASE),
        re.compile(r"(['\"]?(?:api[_-]?key|secret|password|token)['\"]?\s*[:=]\s*['\"])([^'\"]{8,})(['\"])", re.IGNORECASE),
    ]

    @classmethod
    def is_safe_path(cls, path: str) -> bool:
        """
        Guards against Zip Slip (path traversal).
        Returns False if the path traverses upwards or is absolute.
        """
        normalized = os.path.normpath(path)
        if normalized.startswith("..") or os.path.isabs(normalized):
            return False
        return True

    @classmethod
    def is_safe_relative_path(cls, path: str) -> bool:
        """Alias for is_safe_path."""
        return cls.is_safe_path(path)

    @classmethod
    def validate_github_url(cls, url: str) -> bool:
        """
        Validates GitHub repository URL format.
        """
        return bool(cls.GITHUB_REPO_REGEX.match(url.strip()))

    @classmethod
    def is_valid_github_url(cls, url: str) -> bool:
        """
        Alias for validate_github_url.
        """
        return cls.validate_github_url(url)

    @classmethod
    def mask_token(cls, token: Optional[str]) -> str:
        """
        Masks API tokens for safe logging.
        """
        if not token:
            return "<none>"
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    @classmethod
    def sanitize_secrets(cls, text: str) -> str:
        """
        Redacts identifiable secrets, API keys, and credentials from code snippets
        before passing them to the LLM.
        """
        if not text:
            return ""

        sanitized = text
        for pattern in cls.SECRET_PATTERNS:
            if pattern.groups == 3:
                sanitized = pattern.sub(r"\g<1>[REDACTED_SECRET]\g<3>", sanitized)
            else:
                sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

        return sanitized
