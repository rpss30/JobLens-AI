import pandas as pd
import pytest

from scripts import fetch_canada_jobs
from src.ingestion.pipeline_runs import FAILED_STATUS, SUCCESS_STATUS


def test_fetch_all_sources_with_results_tracks_success_and_failure(monkeypatch):
    sources = [
        {
            "company": "GoodCo",
            "source_type": "greenhouse",
            "source_identifier": "goodco",
        },
        {
            "company": "FailCo",
            "source_type": "lever",
            "source_identifier": "failco",
        },
    ]

    def fake_fetch_source_jobs(source):
        if source["company"] == "FailCo":
            raise ValueError("bad source")

        return [{"job_id": "job-1"}]

    monkeypatch.setattr(
        fetch_canada_jobs,
        "fetch_source_jobs",
        fake_fetch_source_jobs,
    )

    jobs, source_results = fetch_canada_jobs.fetch_all_sources_with_results(sources)

    assert jobs == [{"job_id": "job-1"}]
    assert source_results[0].status == SUCCESS_STATUS
    assert source_results[0].job_count == 1
    assert source_results[1].status == FAILED_STATUS
    assert source_results[1].error == "ValueError: bad source"


def test_main_writes_pipeline_summaries(monkeypatch, tmp_path):
    normalized_jobs = [
        {
            "job_id": "greenhouse:goodco:1",
            "title": "Data Engineer",
            "company": "GoodCo",
            "location": "Toronto, ON",
            "description": "Build pipelines.",
            "source": "greenhouse",
            "source_url": "https://example.com/jobs/1",
            "fetched_at": "2026-07-01T12:00:00+00:00",
            "role_category": "Data Engineering",
        }
    ]

    monkeypatch.setattr(
        fetch_canada_jobs,
        "load_employer_sources",
        lambda path: [
            {
                "company": "GoodCo",
                "source_type": "greenhouse",
                "source_identifier": "goodco",
            }
        ],
    )
    monkeypatch.setattr(
        fetch_canada_jobs,
        "fetch_source_jobs",
        lambda source: [{"job_id": "raw-1"}],
    )
    monkeypatch.setattr(
        fetch_canada_jobs,
        "prepare_canada_jobs",
        lambda jobs: normalized_jobs,
    )

    output_path = tmp_path / "canada_jobs.csv"
    summary_path = tmp_path / "fetch-summary.json"
    markdown_path = tmp_path / "fetch-summary.md"

    fetch_canada_jobs.main(
        source_path=tmp_path / "sources.json",
        output_path=output_path,
        summary_path=summary_path,
        summary_markdown_path=markdown_path,
        dataset_name=None,
    )

    output_df = pd.read_csv(output_path)

    assert output_df.iloc[0]["job_id"] == "greenhouse:goodco:1"
    assert '"source_type": "canada_jobs_fetch"' in summary_path.read_text(
        encoding="utf-8"
    )
    assert "## Canada Jobs Fetch Run" in markdown_path.read_text(encoding="utf-8")


def test_main_raises_when_validation_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(
        fetch_canada_jobs,
        "load_employer_sources",
        lambda path: [
            {
                "company": "GoodCo",
                "source_type": "greenhouse",
                "source_identifier": "goodco",
            }
        ],
    )
    monkeypatch.setattr(
        fetch_canada_jobs,
        "fetch_source_jobs",
        lambda source: [{"job_id": "raw-1"}],
    )
    monkeypatch.setattr(
        fetch_canada_jobs,
        "prepare_canada_jobs",
        lambda jobs: [{"job_id": "missing-fields"}],
    )

    summary_path = tmp_path / "fetch-summary.json"

    with pytest.raises(ValueError, match="fetch validation failed"):
        fetch_canada_jobs.main(
            source_path=tmp_path / "sources.json",
            output_path=tmp_path / "canada_jobs.csv",
            summary_path=summary_path,
            dataset_name=None,
        )

    assert '"status": "failed"' in summary_path.read_text(encoding="utf-8")
