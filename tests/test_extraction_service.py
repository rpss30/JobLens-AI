from src.skill_extraction import extraction_service
from src.skill_extraction.extraction_service import (
    DETERMINISTIC_PROVIDER,
    GEMINI_PROVIDER,
    GROQ_PROVIDER,
    extract_skills_ai_first,
)


class FakeGeminiResult:
    def __init__(self, skills):
        self.skills = skills
        self.raw_response = '{"skills": []}'


class FakeGroqResult:
    def __init__(self, skills):
        self.skills = skills
        self.raw_response = '{"skills": []}'


def test_extract_skills_ai_first_uses_groq_when_available(monkeypatch):
    def fake_extract_skills_with_groq(title, description):
        return FakeGroqResult(["python", "sql"])

    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_groq",
        fake_extract_skills_with_groq,
    )

    result = extract_skills_ai_first(
        title="Data Engineer",
        description="Build data pipelines with Python and SQL.",
    )

    assert result.skills == ["python", "sql"]
    assert result.provider == GROQ_PROVIDER
    assert result.error == ""


def test_extract_skills_ai_first_uses_gemini_when_groq_fails(monkeypatch):
    def fake_extract_skills_with_groq(title, description):
        raise RuntimeError("Groq unavailable")

    def fake_extract_skills_with_gemini(title, description):
        return FakeGeminiResult(["python", "aws"])

    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_groq",
        fake_extract_skills_with_groq,
    )
    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_gemini",
        fake_extract_skills_with_gemini,
    )

    result = extract_skills_ai_first(
        title="Cloud Engineer",
        description="Build cloud systems with Python and AWS.",
        max_groq_attempts=1,
    )

    assert result.skills == ["python", "aws"]
    assert result.provider == GEMINI_PROVIDER
    assert result.error == ""


def test_extract_skills_ai_first_uses_deterministic_when_groq_and_gemini_fail(
    monkeypatch,
):
    def fake_extract_skills_with_groq(title, description):
        raise RuntimeError("Groq unavailable")

    def fake_extract_skills_with_gemini(title, description):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_groq",
        fake_extract_skills_with_groq,
    )
    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_gemini",
        fake_extract_skills_with_gemini,
    )

    result = extract_skills_ai_first(
        title="Backend Engineer",
        description="Build APIs with Python, PostgreSQL, Docker, and AWS.",
        max_groq_attempts=1,
        max_gemini_attempts=1,
    )

    assert "python" in result.skills
    assert "postgresql" in result.skills
    assert "docker" in result.skills
    assert "aws" in result.skills
    assert result.provider == DETERMINISTIC_PROVIDER
    assert "Groq attempt 1" in result.error
    assert "Gemini attempt 1" in result.error


def test_extract_skills_ai_first_can_disable_deterministic_fallback(monkeypatch):
    def fake_extract_skills_with_groq(title, description):
        raise RuntimeError("Groq unavailable")

    def fake_extract_skills_with_gemini(title, description):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_groq",
        fake_extract_skills_with_groq,
    )
    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_gemini",
        fake_extract_skills_with_gemini,
    )

    result = extract_skills_ai_first(
        title="Backend Engineer",
        description="Build APIs with Python.",
        use_deterministic_fallback=False,
        max_groq_attempts=1,
        max_gemini_attempts=1,
    )

    assert result.skills == []
    assert result.provider == GEMINI_PROVIDER
    assert "Groq unavailable" in result.error
    assert "Gemini unavailable" in result.error


def test_extract_skills_ai_first_can_skip_groq_primary(monkeypatch):
    def fake_extract_skills_with_gemini(title, description):
        return FakeGeminiResult(["machine learning", "python"])

    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_gemini",
        fake_extract_skills_with_gemini,
    )

    result = extract_skills_ai_first(
        title="ML Engineer",
        description="Build machine learning systems with Python.",
        use_groq_primary=False,
    )

    assert result.skills == ["machine learning", "python"]
    assert result.provider == GEMINI_PROVIDER
    assert result.error == ""


def test_extract_skills_ai_first_retries_groq_before_gemini(monkeypatch):
    calls = {"groq": 0}

    def fake_extract_skills_with_groq(title, description):
        calls["groq"] += 1
        raise RuntimeError("Temporary Groq issue")

    def fake_extract_skills_with_gemini(title, description):
        return FakeGeminiResult(["python"])

    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_groq",
        fake_extract_skills_with_groq,
    )
    monkeypatch.setattr(
        extraction_service,
        "extract_skills_with_gemini",
        fake_extract_skills_with_gemini,
    )
    monkeypatch.setattr(extraction_service.time, "sleep", lambda seconds: None)

    result = extract_skills_ai_first(
        title="Backend Engineer",
        description="Build APIs with Python.",
        max_groq_attempts=2,
        retry_delay_seconds=1,
    )

    assert calls["groq"] == 2
    assert result.provider == GEMINI_PROVIDER
    assert result.skills == ["python"]