from datetime import UTC, datetime

import pandas as pd

from scripts import validate_canada_jobs_snapshot
from src.ingestion.canada_jobs import TARGET_ROLE_CATEGORIES


def build_snapshot_rows(
    *,
    job_count: int = 48,
    fetched_at: str = "2026-06-21T12:00:00+00:00",
) -> list[dict[str, object]]:
    role_categories = sorted(TARGET_ROLE_CATEGORIES)

    return [
        {
            "job_id": f"job-{index}",
            "title": f"Job {index}",
            "company": f"Company {index % 12}",
            "location": f"Location {index % 8}",
            "description": "Build production software.",
            "source": f"source-{index % 2}",
            "source_url": f"https://example.com/jobs/{index}",
            "fetched_at": fetched_at,
            "role_category": role_categories[index % len(role_categories)],
            "skills_text": "python, sql",
            "skill_extraction_provider": "groq",
        }
        for index in range(job_count)
    ]


def test_validate_snapshot_accepts_diverse_fresh_candidate():
    candidate_df = pd.DataFrame(build_snapshot_rows())
    baseline_df = pd.DataFrame(build_snapshot_rows(job_count=60))

    errors, metrics = validate_canada_jobs_snapshot.validate_snapshot(
        candidate_df,
        baseline_df=baseline_df,
        now=datetime(2026, 6, 21, 18, tzinfo=UTC),
    )

    assert errors == []
    assert metrics["job_count"] == 48
    assert metrics["groq_coverage"] == 1.0


def test_validate_snapshot_rejects_large_baseline_drop():
    candidate_df = pd.DataFrame(build_snapshot_rows(job_count=40))
    baseline_df = pd.DataFrame(build_snapshot_rows(job_count=72))

    errors, _ = validate_canada_jobs_snapshot.validate_snapshot(
        candidate_df,
        baseline_df=baseline_df,
        now=datetime(2026, 6, 21, 18, tzinfo=UTC),
    )

    assert any("below 65%" in error for error in errors)


def test_validate_snapshot_rejects_missing_role_and_stale_fetch():
    rows = build_snapshot_rows(fetched_at="2026-06-10T12:00:00+00:00")
    missing_role = sorted(TARGET_ROLE_CATEGORIES)[0]
    replacement_role = sorted(TARGET_ROLE_CATEGORIES)[1]

    for row in rows:
        if row["role_category"] == missing_role:
            row["role_category"] = replacement_role

    errors, _ = validate_canada_jobs_snapshot.validate_snapshot(
        pd.DataFrame(rows),
        now=datetime(2026, 6, 21, 18, tzinfo=UTC),
    )

    assert any(missing_role in error for error in errors)
    assert any("more than three days old" in error for error in errors)


def test_validate_snapshot_rejects_one_stale_row():
    rows = build_snapshot_rows()
    rows[0]["fetched_at"] = "2026-06-10T12:00:00+00:00"

    errors, _ = validate_canada_jobs_snapshot.validate_snapshot(
        pd.DataFrame(rows),
        now=datetime(2026, 6, 21, 18, tzinfo=UTC),
    )

    assert any("more than three days old" in error for error in errors)


def test_build_markdown_summary_includes_baseline_and_coverage():
    metrics = validate_canada_jobs_snapshot.snapshot_metrics(
        pd.DataFrame(build_snapshot_rows())
    )

    summary = validate_canada_jobs_snapshot.build_markdown_summary(
        metrics,
        baseline_count=60,
    )

    assert "## Snapshot Quality" in summary
    assert "Jobs: **48** (previously 60)" in summary
    assert "Groq extraction coverage: **100.0%**" in summary
