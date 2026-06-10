import pytest

from src.skill_extraction.gemini_extractor import parse_gemini_skill_response


def test_parse_gemini_skill_response_returns_normalized_skills():
    response_text = """
    {
        "skills": [" Python ", "SQL", "python", "Machine Learning", "CI/CD"]
    }
    """

    assert parse_gemini_skill_response(response_text) == [
        "python",
        "sql",
        "machine learning",
        "CI/CD",
    ]


def test_parse_gemini_skill_response_respects_max_skills():
    response_text = """
    {
        "skills": ["Python", "SQL", "AWS"]
    }
    """

    assert parse_gemini_skill_response(response_text, max_skills=2) == [
        "python",
        "sql",
    ]


def test_parse_gemini_skill_response_rejects_invalid_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_gemini_skill_response("not json")


def test_parse_gemini_skill_response_requires_skills_list():
    with pytest.raises(ValueError, match="skills"):
        parse_gemini_skill_response('{"tools": ["Python"]}')

    with pytest.raises(ValueError, match="skills"):
        parse_gemini_skill_response('{"skills": "Python"}')