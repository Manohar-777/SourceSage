"""
Shared utility helpers for SourceSage.

Pure functions with no side-effects — safe to call from
any service or router module.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


def filter_files(
    file_tree: list[dict],
    languages: list[str],
) -> list[dict]:
    """Return only the files whose detected language is in *languages*.

    Args:
        file_tree: List of file-info dicts (must contain a ``language`` key).
        languages: Accepted language names (lower-case).

    Returns:
        Filtered list of file-info dicts.
    """
    languages_lower = {lang.lower() for lang in languages}
    return [f for f in file_tree if f.get("language", "").lower() in languages_lower]


def truncate_code(code: str, max_lines: int = 200) -> str:
    """Truncate source code to at most *max_lines* lines.

    If the code is truncated a marker comment is appended so the
    LLM knows the file was trimmed.

    Args:
        code: Full source code string.
        max_lines: Maximum number of lines to retain.

    Returns:
        Possibly truncated source code.
    """
    lines = code.splitlines(keepends=True)
    if len(lines) <= max_lines:
        return code
    truncated = "".join(lines[:max_lines])
    truncated += f"\n# ... [{len(lines) - max_lines} more lines truncated] ...\n"
    return truncated


def sanitize_repo_url(url: str) -> str:
    """Extract the ``owner/repo`` slug from a GitHub URL.

    Handles HTTPS URLs with or without a ``.git`` suffix.

    Args:
        url: Full GitHub repository URL.

    Returns:
        String in the form ``owner/repo``.

    Raises:
        ValueError: If the URL does not look like a GitHub repo.
    """
    parsed = urlparse(str(url))
    path = parsed.path.strip("/")

    # Remove .git suffix if present
    path = re.sub(r"\.git$", "", path)

    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot extract owner/repo from URL: {url}")

    owner, repo = parts[0], parts[1]
    return f"{owner}/{repo}"


def format_file_size(size_bytes: int) -> str:
    """Return a human-readable file size string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string like ``'12.3 KB'`` or ``'1.1 MB'``.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
