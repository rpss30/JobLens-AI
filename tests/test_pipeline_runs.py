from datetime import UTC, datetime, timedelta

from src.ingestion.pipeline_runs import (
    FAILED_STATUS,
    PARTIAL_SUCCESS_STATUS,
    SUCCESS_STATUS,
    SourceFetchResult,
    build_ingestion_run_summary,
    build_markdown_run_summary,
    build_single_stage_run_summary,
    validate_job_records,
    write_run_summary,
)


STARTED_AT = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
COMPLETED_AT = STARTED_AT + timedelta(seconds=15)


def test_build_ingestion_run_summary_marks_partial_success() -> None:
    summary = build_ingestion_run_summary(
        source_type="canada_jobs_fetch",
        started_at=STARTED_AT,
        completed_at=COMPLETED_AT,
        source_results=[
            SourceFetchResult(
                company="GoodCo",
                source_type="greenhouse",
                source_identifier="goodco",
                status=SUCCESS_STATUS,
                job_count=4,
            ),
            SourceFetchResult(
                company="FailCo",
                source_type="lever",
                source_identifier="failco",
                status=FAILED_STATUS,
                error="HTTP 500",
            ),
        ],
        raw_job_count=4,
        processed_job_count=3,
    )

    assert summary.status == PARTIAL_SUCCESS_STATUS
    assert summary.total_sources == 2
    assert summary.successful_sources == 1
    assert summary.failed_sources == 1
    assert summary.error_log == ["FailCo: HTTP 500"]
    assert summary.duration_seconds == 15
    assert summary.metadata["source_results"][0]["job_count"] == 4


def test_build_ingestion_run_summary_fails_on_validation_errors() -> None:
    summary = build_ingestion_run_summary(
        source_type="canada_jobs_fetch",
        started_at=STARTED_AT,
        completed_at=COMPLETED_AT,
        source_results=[
            SourceFetchResult(
                company="GoodCo",
                source_type="greenhouse",
                source_identifier="goodco",
                status=SUCCESS_STATUS,
                job_count=4,
            )
        ],
        raw_job_count=4,
        processed_job_count=4,
        validation_errors=["Duplicate job_id values found: job-1."],
    )

    assert summary.status == FAILED_STATUS
    assert summary.error_log == ["Duplicate job_id values found: job-1."]


def test_build_single_stage_run_summary_fails_when_no_jobs_processed() -> None:
    summary = build_single_stage_run_summary(
        source_type="canada_snapshot_enrichment",
        started_at=STARTED_AT,
        completed_at=COMPLETED_AT,
        raw_job_count=10,
        processed_job_count=0,
        errors=["No skills extracted."],
    )

    assert summary.status == FAILED_STATUS
    assert summary.successful_sources == 0
    assert summary.failed_sources == 1


def test_validate_job_records_detects_missing_and_duplicate_values() -> None:
    errors = validate_job_records(
        [
            {
                "job_id": "job-1",
                "title": "Data Engineer",
                "company": "Example",
                "location": "Toronto, ON",
                "description": "Build pipelines.",
                "source": "greenhouse",
                "source_url": "https://example.com/jobs/1",
                "fetched_at": "2026-07-01T12:00:00+00:00",
                "role_category": "Data Engineering",
            },
            {
                "job_id": "job-1",
                "title": "",
                "company": "Example",
                "location": "Toronto, ON",
                "description": "Build pipelines.",
                "source": "greenhouse",
                "source_url": "https://example.com/jobs/1",
                "fetched_at": "2026-07-01T12:00:00+00:00",
                "role_category": "Data Engineering",
            },
        ]
    )

    assert "Job 2 is missing required fields: title." in errors
    assert "Duplicate job_id values found: job-1." in errors
    assert "Duplicate source_url values found: https://example.com/jobs/1." in errors


def test_write_run_summary_outputs_json(tmp_path) -> None:
    summary = build_single_stage_run_summary(
        source_type="canada_snapshot_enrichment",
        started_at=STARTED_AT,
        completed_at=COMPLETED_AT,
        raw_job_count=1,
        processed_job_count=1,
        metadata={"provider_counts": {"groq": 1}},
    )
    output_path = tmp_path / "run-summary.json"

    write_run_summary(summary, output_path)

    output = output_path.read_text(encoding="utf-8")

    assert '"source_type": "canada_snapshot_enrichment"' in output
    assert '"provider_counts"' in output


def test_build_markdown_run_summary_includes_core_metrics() -> None:
    summary = build_single_stage_run_summary(
        source_type="canada_snapshot_enrichment",
        started_at=STARTED_AT,
        completed_at=COMPLETED_AT,
        raw_job_count=2,
        processed_job_count=1,
    )

    markdown = build_markdown_run_summary(summary)

    assert "## Canada Snapshot Enrichment Run" in markdown
    assert "- Raw jobs: **2**" in markdown
    assert "- Processed jobs: **1**" in markdown
