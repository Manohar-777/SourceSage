"""
Analysis router — the main SSE-streaming endpoint.

POST /api/analyze clones a repository, analyses every file with
Gemini, and streams progress events to the client over SSE.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Header, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import AnalyzeRequest, FileReview
from app.services.code_parser import get_file_metrics
from app.services.gemini_service import GeminiService
from app.services.github_service import (
    cleanup_repo,
    clone_repo,
    get_file_tree,
    read_file_content,
)
from app.services.report_generator import compile_report
from app.utils.helpers import filter_files, truncate_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


def _sse(event: str, data: dict | None = None) -> dict:
    """Format an SSE message dict for ``EventSourceResponse``."""
    return {
        "event": event,
        "data": json.dumps(data or {}, default=str),
    }


async def _analysis_stream(
    request: AnalyzeRequest,
    api_key: str,
) -> AsyncGenerator[dict, None]:
    """Async generator that yields SSE events during analysis.

    Steps:
    1. Clone repository
    2. Discover and filter source files
    3. For each file: parse metrics → Gemini review → yield events
    4. Compile and yield final report
    5. Clean up cloned repo
    """
    repo_path = None

    try:
        # ── Clone ────────────────────────────────────────────
        yield _sse("clone_start", {"repo_url": str(request.repo_url), "branch": request.branch})

        repo_path = await clone_repo(str(request.repo_url), request.branch)

        file_tree = await get_file_tree(repo_path)
        filtered = filter_files(file_tree, request.languages)

        yield _sse(
            "clone_complete",
            {
                "files": len(filtered),
                "total_files": len(file_tree),
                "repo_url": str(request.repo_url),
            },
        )

        if not filtered:
            yield _sse("error", {"message": "No supported source files found in the repository."})
            return

        # ── Analyse each file ────────────────────────────────
        gemini = GeminiService(api_key=api_key)
        file_reviews: list[FileReview] = []

        for file_info in filtered:
            file_path = file_info["path"]
            language = file_info["language"]

            yield _sse("file_start", {"file": file_path, "language": language})

            # Read content
            full_path = repo_path / file_path
            content = await read_file_content(full_path)

            if content is None:
                yield _sse(
                    "file_skip",
                    {"file": file_path, "reason": "File too large or unreadable"},
                )
                continue

            # Static analysis
            metrics = get_file_metrics(content, language)

            # Truncate for LLM context
            truncated = truncate_code(content)

            # Gemini structured review
            review = await gemini.analyze_file(
                code=truncated,
                language=language,
                file_path=file_path,
                metrics=metrics,
            )
            file_reviews.append(review)

            yield _sse(
                "file_complete",
                {"review": review.model_dump(mode="json")},
            )

        # ── Compile report ───────────────────────────────────
        report = compile_report(
            repo_url=str(request.repo_url),
            file_reviews=file_reviews,
            total_files=len(file_tree),
        )

        yield _sse(
            "analysis_complete",
            {"report": report.model_dump(mode="json")},
        )

    except Exception as exc:
        logger.exception("Analysis pipeline error")
        yield _sse("error", {"message": str(exc)})

    finally:
        if repo_path:
            cleanup_repo(repo_path)


@router.post("/analyze")
async def analyze_repository(
    request: AnalyzeRequest,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
        description="Google Gemini API key",
    ),
) -> EventSourceResponse:
    """Analyse a GitHub repository and stream results via SSE.

    The endpoint clones the repository, runs static analysis and
    AI-powered review on each source file, and streams progress
    events to the client.

    Headers:
        X-API-Key: Google Gemini API key.

    Returns:
        ``text/event-stream`` response with SSE events.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required.")

    return EventSourceResponse(
        _analysis_stream(request, x_api_key),
        media_type="text/event-stream",
    )
