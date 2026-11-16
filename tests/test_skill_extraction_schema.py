import pytest

from src.skill_extraction.schema import (
    DESCRIPTION_CHARACTER_BUDGET,
    SKILL_EXTRACTION_PROMPT_VERSION,
    build_structured_skill_extraction_prompt,
    parse_skill_extraction_json,
)


def test_parse_skill_extraction_json_supports_structured_skill_objects():
    result = parse_skill_extraction_json(
        """
        {
          "skills": [
            {
              "name": " Python ",
              "confidence": 1.4,
              "evidence": "Python services"
            },
            {
              "name": "postgres",
              "confidence": 0.85,
              "evidence": "Postgres database"
            },
            {
              "name": "AI",
              "confidence": 0.9,
              "evidence": "generic"
            }
          ]
        }
        """
    )

    assert result.skills == ["python", "postgresql"]
    assert result.skill_items[0].confidence == 1.0
    assert result.skill_items[1].confidence == 0.85
    assert result.skill_items[1].evidence == "Postgres database"
    assert result.prompt_version == SKILL_EXTRACTION_PROMPT_VERSION


def test_parse_skill_extraction_json_supports_legacy_string_lists():
    result = parse_skill_extraction_json(
        '{"skills": ["JS", "Node", "K8s", "REST API", "JS"]}'
    )

    assert result.skills == [
        "javascript",
        "node.js",
        "kubernetes",
        "REST APIs",
    ]
    assert result.skill_items[0].confidence == 1.0


def test_parse_skill_extraction_json_rejects_invalid_payloads():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_skill_extraction_json("not json")

    with pytest.raises(ValueError, match="JSON object"):
        parse_skill_extraction_json('["Python"]')

    with pytest.raises(ValueError, match="skills"):
        parse_skill_extraction_json('{"tools": ["Python"]}')


def test_build_structured_skill_extraction_prompt_includes_schema_and_version():
    prompt = build_structured_skill_extraction_prompt(
        title="Backend Engineer",
        description="Build APIs with Python.",
    )

    assert SKILL_EXTRACTION_PROMPT_VERSION in prompt
    assert '"confidence"' in prompt
    assert '"evidence"' in prompt
    assert "Do not include soft skills" in prompt


def test_build_structured_skill_extraction_prompt_reaches_the_requirements():
    """
    Requirements sit after the company preamble, so the budget has to be wide
    enough to reach them. At 4,000 characters a real posting lost its whole
    requirements section and the model answered with an empty skills array,
    exactly as its own rules tell it to when no skills are present.
    """
    preamble = "About the company. " * 250  # ~4,750 characters of boilerplate
    description = f"{preamble}What you bring: experience with Kubernetes."

    prompt = build_structured_skill_extraction_prompt(
        title="Backend Engineer",
        description=description,
    )

    assert len(preamble) > 4_000
    assert "experience with Kubernetes" in prompt


def test_build_structured_skill_extraction_prompt_still_bounds_the_description():
    prompt = build_structured_skill_extraction_prompt(
        title="Backend Engineer",
        description="x" * (DESCRIPTION_CHARACTER_BUDGET * 3),
    )

    assert "x" * DESCRIPTION_CHARACTER_BUDGET in prompt
    assert "x" * (DESCRIPTION_CHARACTER_BUDGET + 1) not in prompt
