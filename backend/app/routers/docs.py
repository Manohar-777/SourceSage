"""
Documentation generation router.

POST /api/generate-docs clones a repository, reads source files,
and uses Gemini to produce a README and per-file documentation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException

from app.models.schemas import DocGenerationRequest, GeneratedDocs
from app.services.gemini_service import GeminiService
from app.services.github_service import (
    cleanup_repo,
    clone_repo,
    get_file_tree,
    read_file_content,
)
from app.utils.helpers import truncate_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documentation"])


@router.post("/generate-docs", response_model=GeneratedDocs)
async def generate_docs(
    request: DocGenerationRequest,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
        description="Google Gemini API key",
    ),
) -> GeneratedDocs:
    """Generate documentation for a GitHub repository.

    Clones the repository, reads source files (optionally filtered
    by ``file_paths``), and uses Gemini to produce:
    - A README.md
    - Per-file documentation strings

    Headers:
        X-API-Key: Google Gemini API key.

    Returns:
        :class:`GeneratedDocs` with README content and file docs.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required.")

    repo_path = None

    try:
        # ── Clone ────────────────────────────────────────────
        repo_path = await clone_repo(request.repo_url, request.branch)
        file_tree = await get_file_tree(repo_path)

        if not file_tree:
            raise HTTPException(
                status_code=404,
                detail="No supported source files found in the repository.",
            )

        # ── Filter files if specific paths requested ─────────
        if request.file_paths:
            requested = set(request.file_paths)
            file_tree = [f for f in file_tree if f["path"] in requested]

        gemini = GeminiService(api_key=x_api_key)

        # ── Read files and generate per-file docs ────────────
        file_docs: dict[str, str] = {}
        sample_code: dict[str, str] = {}

        for file_info in file_tree:
            fpath = file_info["path"]
            language = file_info["language"]

            full_path = repo_path / fpath
            content = await read_file_content(full_path)

            if content is None:
                continue

            sample_code[fpath] = content[:1000]  # keep sample for README

            truncated = truncate_code(content)
            doc = await gemini.generate_documentation(
                code=truncated,
                language=language,
                file_path=fpath,
            )
            file_docs[fpath] = doc

        # ── Generate README ──────────────────────────────────
        readme = await gemini.generate_readme(file_tree, sample_code)

        return GeneratedDocs(
            readme_content=readme,
            file_docs=file_docs,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Documentation generation error")
        raise HTTPException(
            status_code=500,
            detail=f"Documentation generation failed: {exc}",
        ) from exc

    finally:
        if repo_path:
            cleanup_repo(repo_path)
