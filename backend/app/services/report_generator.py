"""
Report generation and score aggregation for SourceSage.

Compiles individual :class:`FileReview` objects into a single
:class:`AnalysisReport` with weighted scoring and issue counts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import AnalysisReport, FileReview


def calculate_overall_score(file_reviews: list[FileReview]) -> float:
    """Compute a weighted-average quality score across all reviewed files.

    Weighting scheme:
    - Files with ``critical`` issues are given 1.5× weight so they
      drag the average down more.
    - Files with no issues at all are given 0.8× weight to avoid
      inflating the score with trivially small files.

    Args:
        file_reviews: List of per-file review objects.

    Returns:
        Overall score between 0 and 100 (rounded to one decimal).
    """
    if not file_reviews:
        return 100.0

    total_weight = 0.0
    weighted_sum = 0.0

    for review in file_reviews:
        has_critical = any(i.severity == "critical" for i in review.issues)
        has_issues = len(review.issues) > 0

        if has_critical:
            weight = 1.5
        elif not has_issues:
            weight = 0.8
        else:
            weight = 1.0

        weighted_sum += review.score * weight
        total_weight += weight

    return round(weighted_sum / total_weight, 1) if total_weight else 100.0


def compile_report(
    repo_url: str,
    file_reviews: list[FileReview],
    total_files: int | None = None,
) -> AnalysisReport:
    """Aggregate file reviews into a top-level :class:`AnalysisReport`.

    Args:
        repo_url: The original repository URL.
        file_reviews: Per-file review results.
        total_files: Total files discovered in the repo
            (defaults to ``len(file_reviews)``).

    Returns:
        Fully populated :class:`AnalysisReport`.
    """
    critical = 0
    warning = 0
    info = 0

    for review in file_reviews:
        for issue in review.issues:
            if issue.severity == "critical":
                critical += 1
            elif issue.severity == "warning":
                warning += 1
            else:
                info += 1

    overall_score = calculate_overall_score(file_reviews)

    # Build executive summary
    if overall_score >= 90:
        quality_label = "excellent"
    elif overall_score >= 75:
        quality_label = "good"
    elif overall_score >= 50:
        quality_label = "needs improvement"
    else:
        quality_label = "poor"

    summary = (
        f"Repository analysis complete. "
        f"Reviewed {len(file_reviews)} file(s) with an overall quality "
        f"score of {overall_score}/100 ({quality_label}). "
        f"Found {critical} critical issue(s), {warning} warning(s), "
        f"and {info} informational note(s)."
    )

    return AnalysisReport(
        repo_url=str(repo_url),
        total_files=total_files if total_files is not None else len(file_reviews),
        files_analyzed=len(file_reviews),
        file_reviews=file_reviews,
        overall_score=overall_score,
        critical_count=critical,
        warning_count=warning,
        info_count=info,
        summary=summary,
        generated_at=datetime.now(timezone.utc),
    )
