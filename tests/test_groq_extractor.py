import pytest

from src.skill_extraction import groq_extractor
from src.skill_extraction.groq_extractor import parse_groq_skill_response


def test_parse_groq_skill_response_returns_normalized_skills():
    response_text = """
    {
        "skills": [" Python ", "SQL", "python", "Machine Learning", "CI/CD"]
    }
    """

    assert parse_groq_skill_response(response_text) == [
        "python",
        "sql",
        "machine learning",
        "CI/CD",
    ]


def test_parse_groq_skill_response_filters_generic_terms():
    response_text = """
    {
        "skills": ["Python", "AI", "systems", "SQL"]
    }
    """

    assert parse_groq_skill_response(response_text) == ["python", "sql"]


def test_parse_groq_skill_response_respects_max_skills():
    response_text = """
    {
        "skills": ["Python", "SQL", "AWS"]
    }
    """

    assert parse_groq_skill_response(response_text, max_skills=2) == [
        "python",
        "sql",
    ]


def test_parse_groq_skill_response_rejects_invalid_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_groq_skill_response("not json")


def test_parse_groq_skill_response_requires_skills_list():
    with pytest.raises(ValueError, match="skills"):
        parse_groq_skill_response('{"tools": ["Python"]}')

    with pytest.raises(ValueError, match="skills"):
        parse_groq_skill_response('{"skills": "Python"}')

class FakeCompletions:
    """Minimal stand-in for the Groq chat completions client."""

    def __init__(self, retired_models: set[str], response_text: str) -> None:
        self.retired_models = retired_models
        self.response_text = response_text
        self.requested_models: list[str] = []

    def create(self, *, model: str, **_: object):
        self.requested_models.append(model)

        if model in self.retired_models:
            raise RuntimeError(
                "Error code: 404 - {'error': {'message': 'The model "
                f"`{model}` does not exist or you do not have access to it.', "
                "'code': 'model_not_found'}}"
            )

        message = type("Message", (), {"content": self.response_text})
        choice = type("Choice", (), {"message": message()})
        return type("Completion", (), {"choices": [choice()]})()


def build_fake_groq(monkeypatch, retired_models: set[str]) -> FakeCompletions:
    completions = FakeCompletions(retired_models, '{"skills": ["Python", "SQL"]}')

    class FakeGroq:
        def __init__(self, **_: object) -> None:
            self.chat = type("Chat", (), {"completions": completions})()

    monkeypatch.setattr(groq_extractor, "Groq", FakeGroq)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("GROQ_MODEL_FALLBACKS", raising=False)
    monkeypatch.setattr(groq_extractor, "load_dotenv", lambda *a, **k: None)
    groq_extractor.reset_unavailable_models()

    return completions


def test_extract_skills_falls_back_when_the_model_has_been_retired(monkeypatch):
    completions = build_fake_groq(
        monkeypatch,
        retired_models={groq_extractor.DEFAULT_GROQ_MODEL},
    )

    result = groq_extractor.extract_skills_with_groq(
        title="Data Engineer",
        description="Python and SQL pipelines.",
    )

    assert result.skills == ["python", "sql"]
    # The recorded model is the one that answered, so the snapshot keeps accurate
    # provenance rather than naming a model that never ran.
    assert result.model == groq_extractor.DEFAULT_GROQ_MODEL_FALLBACKS[0]
    assert completions.requested_models == [
        groq_extractor.DEFAULT_GROQ_MODEL,
        groq_extractor.DEFAULT_GROQ_MODEL_FALLBACKS[0],
    ]


def test_a_retired_model_is_not_retried_for_every_posting(monkeypatch):
    completions = build_fake_groq(
        monkeypatch,
        retired_models={groq_extractor.DEFAULT_GROQ_MODEL},
    )

    for _ in range(3):
        groq_extractor.extract_skills_with_groq(
            title="Data Engineer",
            description="Python and SQL pipelines.",
        )

    # The dead model is asked once, not once per posting.
    assert completions.requested_models.count(groq_extractor.DEFAULT_GROQ_MODEL) == 1


def test_extract_skills_raises_when_no_configured_model_is_available(monkeypatch):
    build_fake_groq(
        monkeypatch,
        retired_models={
            groq_extractor.DEFAULT_GROQ_MODEL,
            *groq_extractor.DEFAULT_GROQ_MODEL_FALLBACKS,
        },
    )

    with pytest.raises(RuntimeError, match="No configured Groq model is available"):
        groq_extractor.extract_skills_with_groq(
            title="Data Engineer",
            description="Python and SQL pipelines.",
        )


def test_a_rate_limit_does_not_disqualify_the_model(monkeypatch):
    """Only a retired model may be skipped; transient errors must surface."""
    completions = build_fake_groq(monkeypatch, retired_models=set())

    def rate_limited(*, model: str, **_: object):
        completions.requested_models.append(model)
        raise RuntimeError("Error code: 429 - rate_limit_exceeded")

    monkeypatch.setattr(completions, "create", rate_limited)

    with pytest.raises(RuntimeError, match="429"):
        groq_extractor.extract_skills_with_groq(
            title="Data Engineer",
            description="Python and SQL pipelines.",
        )

    assert completions.requested_models == [groq_extractor.DEFAULT_GROQ_MODEL]


def test_an_explicit_model_is_never_silently_replaced(monkeypatch):
    build_fake_groq(monkeypatch, retired_models={"pinned-model"})

    with pytest.raises(RuntimeError, match="No configured Groq model is available"):
        groq_extractor.extract_skills_with_groq(
            title="Data Engineer",
            description="Python and SQL pipelines.",
            model="pinned-model",
        )


def test_configured_fallbacks_override_the_defaults(monkeypatch):
    completions = build_fake_groq(monkeypatch, retired_models={"first-choice"})
    monkeypatch.setenv("GROQ_MODEL", "first-choice")
    monkeypatch.setenv("GROQ_MODEL_FALLBACKS", "second-choice, third-choice")

    result = groq_extractor.extract_skills_with_groq(
        title="Data Engineer",
        description="Python and SQL pipelines.",
    )

    assert result.model == "second-choice"
    assert completions.requested_models == ["first-choice", "second-choice"]
