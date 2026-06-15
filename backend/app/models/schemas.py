"""
Pydantic v2 schemas for SourceSage API requests and responses.

Every model uses strict validation and is designed for both
FastAPI serialization and Gemini structured-output parsing.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


# ── Request Models ───────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Incoming request to analyze a GitHub repository."""

    repo_url: HttpUrl = Field(
        ...,
        description="Full HTTPS URL of the GitHub repository to analyse.",
        examples=["https://github.com/owner/repo"],
    )
    languages: list[str] = Field(
        default=["python", "javascript", "typescript", "java"],
        description="Programming languages to include in the analysis.",
    )
    review_depth: str = Field(
        default="standard",
        description="Review depth: 'quick', 'standard', or 'thorough'.",
    )
    branch: str | None = Field(
        default=None,
        description="Optional Git branch name to clone/analyze.",
    )


class DocGenerationRequest(BaseModel):
    """Request to generate documentation for a repository."""

    repo_url: str = Field(
        ...,
        description="GitHub repository URL.",
    )
    file_paths: list[str] | None = Field(
        default=None,
        description="Specific file paths to document. If None, all files are documented.",
    )
    branch: str | None = Field(
        default=None,
        description="Optional Git branch name to clone/analyze.",
    )


# ── Analysis Result Models ───────────────────────────────────

class CodeIssue(BaseModel):
    """A single code-quality issue detected during review."""

    severity: Literal["critical", "warning", "info"] = Field(
        ..., description="Issue severity level."
    )
    category: str = Field(
        ..., description="Category such as 'security', 'performance', 'style'."
    )
    file_path: str = Field(..., description="Relative path of the affected file.")
    line_number: int | None = Field(
        default=None, description="Approximate line number, if applicable."
    )
    description: str = Field(..., description="Human-readable description of the issue.")
    suggestion: str = Field(..., description="Actionable fix suggestion.")
    code_snippet: str | None = Field(
        default=None, description="Relevant code snippet."
    )


class FileReview(BaseModel):
    """Aggregated review for a single source file."""

    file_path: str = Field(..., description="Relative path of the reviewed file.")
    language: str = Field(..., description="Detected programming language.")
    issues: list[CodeIssue] = Field(default_factory=list)
    score: float = Field(
        ..., ge=0, le=100, description="Quality score from 0 (worst) to 100 (best)."
    )
    summary: str = Field(..., description="One-paragraph review summary.")


class AnalysisReport(BaseModel):
    """Top-level report aggregating all file reviews."""

    repo_url: str
    total_files: int = Field(..., description="Total files discovered in the repo.")
    files_analyzed: int = Field(..., description="Files that were actually reviewed.")
    file_reviews: list[FileReview] = Field(default_factory=list)
    overall_score: float = Field(
        ..., ge=0, le=100, description="Weighted overall quality score."
    )
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    summary: str = Field(..., description="Executive summary of the analysis.")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Documentation Models ─────────────────────────────────────

class GeneratedDocs(BaseModel):
    """Documentation artefacts produced by the docs endpoint."""

    readme_content: str = Field(..., description="Generated README.md content.")
    file_docs: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of file path → generated documentation string.",
    )


# ── SSE Event Model ──────────────────────────────────────────

class StreamEvent(BaseModel):
    """Server-Sent Event payload."""

    event: str = Field(..., description="Event name, e.g. 'file_complete'.")
    data: dict = Field(default_factory=dict, description="Event payload.")
