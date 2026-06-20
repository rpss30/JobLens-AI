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
