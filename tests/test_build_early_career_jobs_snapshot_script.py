from datetime import UTC, datetime

import pandas as pd

from scripts import build_early_career_jobs_snapshot
from src.ingestion.job_page_hydrator import JobPageHydrationResult


def raw_job(**overrides):
    row = {
        "job_id": "simplify_new_grad:example:1",
        "title": "Software Engineer New Grad",
        "company": "ExampleCo",
        "location": "Seattle, WA",
        "description": "New-grad index listing for Software Engineering.",
        "experience_level": "Entry Level",
        "source": "simplify_new_grad",
        "source_url": "https://example.com/job",
        "fetched_at": "2026-08-24T12:00:00+00:00",
        "role_category": "Software Engineering",
    }
    row.update(overrides)
    return row


def test_build_processed_row_uses_hydrated_description(monkeypatch) -> None:
    monkeypatch.setattr(
        build_early_career_jobs_snapshot,
        "hydrate_job_page",
        lambda *args, **kwargs: JobPageHydrationResult(
            description="Build APIs with Python, SQL, Docker, and React.",
            provider="apply_page",
            status_code=200,
        ),
    )

    row = build_early_career_jobs_snapshot.build_processed_row(raw_job())

    assert row["description"] == "Build APIs with Python, SQL, Docker, and React."
    assert row["description_hydration_provider"] == "apply_page"
    assert row["description_hydration_status_code"] == 200
    assert row["extracted_skills"] == ["python", "sql", "docker", "react"]
    assert row["skills_text"] == "python, sql, docker, react"
    assert row["skill_extraction_provider"] == "deterministic_skill_dictionary"


def test_build_processed_row_falls_back_to_index_description(monkeypatch) -> None:
    monkeypatch.setattr(
        build_early_career_jobs_snapshot,
        "hydrate_job_page",
        lambda *args, **kwargs: JobPageHydrationResult(
            description="",
            provider="source_index_fallback",
            status_code=200,
            error="application page did not expose enough static job text",
        ),
    )

    row = build_early_career_jobs_snapshot.build_processed_row(
        raw_job(description="Role: Software Engineer New Grad. Apply URL: https://example.com/job."),
    )

    assert row["description"].startswith("Role: Software Engineer")
    assert row["description_hydration_provider"] == "source_index_fallback"
    assert "not expose enough" in row["description_hydration_error"]


def test_main_writes_processed_dataset_and_summary(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "simplify.csv"
    output_path = tmp_path / "early_career.csv"
    summary_path = tmp_path / "summary.json"
    markdown_path = tmp_path / "summary.md"

    pd.DataFrame(
        [
            raw_job(),
            raw_job(
                job_id="simplify_new_grad:example:2",
                title="Data Engineer New Grad",
                source_url="https://example.com/data",
                role_category="Data Engineering",
            ),
        ]
    ).to_csv(input_path, index=False)

    monkeypatch.setattr(
        build_early_career_jobs_snapshot,
        "current_utc_time",
        lambda: datetime(2026, 8, 24, 12, tzinfo=UTC),
    )
    monkeypatch.setattr(
        build_early_career_jobs_snapshot,
        "hydrate_job_page",
        lambda *args, **kwargs: JobPageHydrationResult(
            description="Build data APIs with Python and SQL.",
            provider="apply_page",
            status_code=200,
        ),
    )

    build_early_career_jobs_snapshot.main(
        input_path=input_path,
        output_path=output_path,
        summary_path=summary_path,
        summary_markdown_path=markdown_path,
    )

    output_df = pd.read_csv(output_path)

    assert output_df["skills_text"].tolist() == ["python, sql", "python, sql"]
    assert '"source_type": "early_career_global_build"' in summary_path.read_text(
        encoding="utf-8"
    )
    assert '"skill_coverage": 1.0' in summary_path.read_text(encoding="utf-8")
    assert "## Early Career Global Build Run" in markdown_path.read_text(
        encoding="utf-8"
    )
