"""
GitHub repository operations for SourceSage.

Handles cloning, file-tree discovery, reading source files,
and cleanup of temporary repo directories.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path

from git import Repo

from app.config import settings

logger = logging.getLogger(__name__)

# ── Supported file extensions and their language mapping ─────

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
}


def detect_language(file_path: str) -> str:
    """Map a file path's extension to a language name.

    Args:
        file_path: Relative or absolute path to a source file.

    Returns:
        Lower-case language name, or ``'unknown'`` if the
        extension is not in :data:`SUPPORTED_EXTENSIONS`.
    """
    suffix = Path(file_path).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(suffix, "unknown")


async def clone_repo(repo_url: str) -> Path:
    """Clone a GitHub repository (shallow, depth=1) into a temp directory.

    The clone runs in a thread executor so it never blocks the
    event loop.

    Args:
        repo_url: HTTPS URL of the repository.

    Returns:
        Path to the cloned repository root.

    Raises:
        RuntimeError: If the clone operation fails.
    """
    repo_dir = settings.temp_path / f"repo_{uuid.uuid4().hex[:12]}"
    repo_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Cloning %s → %s (depth=1)", repo_url, repo_dir)

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: Repo.clone_from(
                str(repo_url),
                str(repo_dir),
                depth=1,
                single_branch=True,
            ),
        )
    except Exception as exc:
        # Clean up the empty directory on failure
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to clone repository: {exc}") from exc

    logger.info("Clone complete: %s", repo_dir)
    return repo_dir


async def get_file_tree(
    repo_path: Path,
    extensions: list[str] | None = None,
) -> list[dict]:
    """Walk the repository and return metadata for each source file.

    Args:
        repo_path: Root directory of the cloned repo.
        extensions: Whitelist of extensions (with leading dot).
            Defaults to all keys in :data:`SUPPORTED_EXTENSIONS`.

    Returns:
        List of dicts with keys ``path``, ``size``, ``language``.
    """
    if extensions is None:
        extensions = list(SUPPORTED_EXTENSIONS.keys())

    extensions_set = set(extensions)
    file_tree: list[dict] = []

    def _walk() -> list[dict]:
        results: list[dict] = []
        for file in repo_path.rglob("*"):
            if not file.is_file():
                continue
            if file.suffix.lower() not in extensions_set:
                continue
            # Skip hidden dirs and common non-source directories
            parts = file.relative_to(repo_path).parts
            if any(part.startswith(".") or part in {"node_modules", "__pycache__", "venv", ".venv", "dist", "build"} for part in parts):
                continue

            relative = str(file.relative_to(repo_path)).replace("\\", "/")
            results.append(
                {
                    "path": relative,
                    "size": file.stat().st_size,
                    "language": detect_language(relative),
                }
            )
        return results

    loop = asyncio.get_running_loop()
    file_tree = await loop.run_in_executor(None, _walk)
    logger.info("Discovered %d source files in %s", len(file_tree), repo_path)
    return file_tree


async def read_file_content(
    file_path: Path,
    max_size_kb: int | None = None,
) -> str | None:
    """Read a source file's text content.

    Args:
        file_path: Absolute path to the file.
        max_size_kb: Skip files larger than this (in KB).
            Defaults to :pyattr:`settings.MAX_FILE_SIZE_KB`.

    Returns:
        File contents as a string, or ``None`` if the file is
        too large or unreadable.
    """
    if max_size_kb is None:
        max_size_kb = settings.MAX_FILE_SIZE_KB

    try:
        size_kb = file_path.stat().st_size / 1024
        if size_kb > max_size_kb:
            logger.debug("Skipping %s (%.1f KB > %d KB limit)", file_path, size_kb, max_size_kb)
            return None

        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(
            None,
            lambda: file_path.read_text(encoding="utf-8", errors="replace"),
        )
        return content
    except Exception as exc:
        logger.warning("Could not read %s: %s", file_path, exc)
        return None


def cleanup_repo(repo_path: Path) -> None:
    """Remove a previously cloned repository directory.

    Args:
        repo_path: Root directory of the cloned repo.
    """
    try:
        shutil.rmtree(repo_path, ignore_errors=True)
        logger.info("Cleaned up %s", repo_path)
    except Exception as exc:
        logger.warning("Cleanup failed for %s: %s", repo_path, exc)
