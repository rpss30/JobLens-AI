from scripts import build_canada_jobs_snapshot


class FakeGroqResult:
    skills = ["python", "sql", "AWS"]


def test_extract_skills_groq_first_uses_groq(monkeypatch):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_with_groq",
        lambda title, description: FakeGroqResult(),
    )

    skills, provider, error = (
        build_canada_jobs_snapshot.extract_skills_groq_first(
            title="Data Engineer",
            description="Build pipelines with Python, SQL, and AWS.",
        )
    )

    assert skills == ["python", "sql", "AWS"]
    assert provider == "groq"
    assert error == ""


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

    skills, provider, error = (
        build_canada_jobs_snapshot.extract_skills_groq_first(
            title="Backend Engineer",
            description="Build APIs with Python.",
        )
    )

    assert skills == ["python"]
    assert provider == "deterministic_fallback"
    assert "Groq attempt 2" in error


def test_process_selected_jobs_writes_incremental_checkpoint(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_groq_first",
        lambda **kwargs: (["python"], "groq", ""),
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
                "fetched_at": "2026-06-14T00:00:00+00:00",
            }
        },
        delay_seconds=0,
    )

    assert rows[0]["extracted_skills"] == ["python"]
    assert rows[0]["fetched_at"] == "2026-06-21T00:00:00+00:00"


def test_process_selected_jobs_reextracts_changed_descriptions(monkeypatch):
    monkeypatch.setattr(
        build_canada_jobs_snapshot,
        "extract_skills_groq_first",
        lambda **kwargs: (["python", "sql"], "groq", ""),
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
