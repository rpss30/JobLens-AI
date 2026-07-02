from scripts import build_canada_jobs_snapshot
from src.skill_extraction.schema import ExtractedSkill


class FakeGroqResult:
    skills = ["python", "sql", "AWS"]
    skill_items = [
        ExtractedSkill(name="python", confidence=0.9, evidence="Python"),
        ExtractedSkill(name="sql", confidence=0.8, evidence="SQL"),
        ExtractedSkill(name="AWS", confidence=0.7, evidence="AWS"),
    ]
    model = "llama-test"
    prompt_version = "skill-extraction-v2"


def test_extract_skills_groq_first_uses_groq(monkeypatch):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_with_groq",
        lambda title, description: FakeGroqResult(),
    )

    result = build_canada_jobs_snapshot.extract_skills_groq_first(
        title="Data Engineer",
        description="Build pipelines with Python, SQL, and AWS.",
    )

    assert result.skills == ["python", "sql", "AWS"]
    assert result.provider == "groq"
    assert result.error == ""
    assert result.model == "llama-test"
    assert result.prompt_version == "skill-extraction-v2"
    assert result.confidence == 0.8


def test_extract_skills_groq_first_falls_back_after_failures(monkeypatch):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_with_groq",
        lambda title, description: (_ for _ in ()).throw(
            RuntimeError("Groq unavailable")
        ),
    )
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_deterministic",
        lambda description: ["python"],
    )
    monkeypatch.setattr(
        build_canada_jobs_snapshot.time,
        "sleep",
        lambda seconds: None,
    )

    result = build_canada_jobs_snapshot.extract_skills_groq_first(
        title="Backend Engineer",
        description="Build APIs with Python.",
    )

    assert result.skills == ["python"]
    assert result.provider == "deterministic_fallback"
    assert result.model == build_canada_jobs_snapshot.DETERMINISTIC_FALLBACK_MODEL
    assert result.prompt_version == (
        build_canada_jobs_snapshot.DETERMINISTIC_FALLBACK_PROMPT_VERSION
    )
    assert result.confidence == 0.5
    assert "Groq attempt 2" in result.error


def test_process_selected_jobs_writes_incremental_checkpoint(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_groq_first",
        lambda **kwargs: build_canada_jobs_snapshot.SnapshotSkillExtractionResult(
            skills=["python"],
            provider="groq",
            model="llama-test",
            prompt_version="skill-extraction-v2",
            confidence=0.9,
        ),
    )
    monkeypatch.setattr(
        build_canada_jobs_snapshot.time,
        "sleep",
        lambda seconds: None,
    )
    checkpoint_path = tmp_path / "snapshot.csv"

    rows = build_canada_jobs_snapshot.process_selected_jobs(
        [
            {
                "job_id": "job-1",
                "title": "Data Engineer",
                "company": "Example",
                "description": "Build pipelines with Python.",
            }
        ],
        checkpoint_path=checkpoint_path,
        delay_seconds=0,
    )

    assert checkpoint_path.exists()
    assert rows[0]["skill_extraction_provider"] == "groq"
    assert rows[0]["skill_extraction_model"] == "llama-test"
    assert rows[0]["skill_extraction_prompt_version"] == "skill-extraction-v2"
    assert rows[0]["skill_extraction_confidence"] == 0.9


def test_process_selected_jobs_reuses_skills_with_current_source_metadata(
    monkeypatch,
):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_groq_first",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Groq should not run for an unchanged description")
        ),
    )

    rows = build_canada_jobs_snapshot.process_selected_jobs(
        [
            {
                "job_id": "job-1",
                "title": "Data Engineer",
                "company": "Example",
                "description": "Build pipelines with Python.",
                "fetched_at": "2026-06-21T00:00:00+00:00",
            }
        ],
        existing_rows={
            "job-1": {
                "job_id": "job-1",
                "clean_description": "build pipelines with python.",
                "extracted_skills": ["python"],
                "skills_text": "python",
                "skill_extraction_provider": "groq",
                "skill_extraction_error": "",
                "skill_extraction_model": "llama-reused",
                "skill_extraction_prompt_version": "skill-extraction-v2",
                "skill_extraction_confidence": 0.88,
                "fetched_at": "2026-06-14T00:00:00+00:00",
            }
        },
        delay_seconds=0,
    )

    assert rows[0]["extracted_skills"] == ["python"]
    assert rows[0]["fetched_at"] == "2026-06-21T00:00:00+00:00"
    assert rows[0]["skill_extraction_model"] == "llama-reused"
    assert rows[0]["skill_extraction_confidence"] == 0.88


def test_process_selected_jobs_reextracts_changed_descriptions(monkeypatch):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_groq_first",
        lambda **kwargs: build_canada_jobs_snapshot.SnapshotSkillExtractionResult(
            skills=["python", "sql"],
            provider="groq",
            model="llama-test",
            prompt_version="skill-extraction-v2",
            confidence=0.91,
        ),
    )
    monkeypatch.setattr(
        build_canada_jobs_snapshot.time,
        "sleep",
        lambda seconds: None,
    )

    rows = build_canada_jobs_snapshot.process_selected_jobs(
        [
            {
                "job_id": "job-1",
                "title": "Data Engineer",
                "company": "Example",
                "description": "Build new pipelines with Python and SQL.",
            }
        ],
        existing_rows={
            "job-1": {
                "clean_description": "build pipelines with python",
                "extracted_skills": ["python"],
                "skills_text": "python",
                "skill_extraction_provider": "groq",
            }
        },
        delay_seconds=0,
    )

    assert rows[0]["extracted_skills"] == ["python", "sql"]


def test_build_snapshot_run_summary_counts_providers_and_skips(tmp_path):
    summary = build_canada_jobs_snapshot.build_snapshot_run_summary(
        selected_jobs=[
            {"job_id": "job-1"},
            {"job_id": "job-2"},
        ],
        processed_rows=[
            {
                "job_id": "job-1",
                "skill_extraction_provider": "groq",
                "skill_extraction_error": "",
                "skill_extraction_prompt_version": "skill-extraction-v2",
                "skill_extraction_confidence": 0.8,
            }
        ],
        started_at=build_canada_jobs_snapshot.current_utc_time(),
        output_path=tmp_path / "snapshot.csv",
    )

    assert summary.source_type == "canada_snapshot_enrichment"
    assert summary.raw_job_count == 2
    assert summary.processed_job_count == 1
    assert summary.metadata["provider_counts"] == {"groq": 1}
    assert summary.metadata["prompt_version_counts"] == {"skill-extraction-v2": 1}
    assert summary.metadata["average_extraction_confidence"] == 0.8
    assert summary.metadata["skipped_count"] == 1
    assert summary.error_log == [
        "1 selected postings were skipped during enrichment."
    ]


def test_main_writes_snapshot_run_summaries(monkeypatch, tmp_path):
    input_path = tmp_path / "canada_jobs.csv"
    output_path = tmp_path / "snapshot.csv"
    summary_path = tmp_path / "build-summary.json"
    markdown_path = tmp_path / "build-summary.md"
    input_path.write_text("job_id,title\njob-1,Data Engineer\n", encoding="utf-8")

    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "select_balanced_jobs",
        lambda jobs, **kwargs: [
            {
                "job_id": "job-1",
                "title": "Data Engineer",
                "company": "Example",
                "description": "Build pipelines with Python.",
            }
        ],
    )
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "process_selected_jobs",
        lambda jobs, **kwargs: [
            {
                **jobs[0],
                "clean_title": "data engineer",
                "clean_description": "build pipelines with python.",
                "extracted_skills": ["Python"],
                "skills_text": "Python",
                "role_category": "Data Engineering",
                "skill_extraction_provider": "groq",
                "skill_extraction_error": "",
            }
        ],
    )

    build_canada_jobs_snapshot.main(
        input_path=input_path,
        output_path=output_path,
        delay_seconds=0,
        summary_path=summary_path,
        summary_markdown_path=markdown_path,
        dataset_name=None,
    )

    assert output_path.exists()
    assert '"source_type": "canada_snapshot_enrichment"' in summary_path.read_text(
        encoding="utf-8"
    )
    assert "## Canada Snapshot Enrichment Run" in markdown_path.read_text(
        encoding="utf-8"
    )
