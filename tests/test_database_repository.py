# tests/test_database_repository.py

from src.database.repository import normalize_skill_name, parse_skills


def test_normalize_skill_name_lowercases_and_strips_whitespace():
    assert normalize_skill_name("  Python  ") == "python"


def test_parse_skills_from_list():
    assert parse_skills(["Python", "SQL"]) == ["Python", "SQL"]


def test_parse_skills_from_stringified_list():
    assert parse_skills("['Python', 'SQL']") == ["Python", "SQL"]


def test_parse_skills_from_comma_separated_string():
    assert parse_skills("Python, SQL, AWS") == ["Python", "SQL", "AWS"]


def test_parse_skills_from_empty_string():
    assert parse_skills("") == []


def test_parse_skills_removes_blank_items_from_list():
    assert parse_skills(["Python", "", " SQL "]) == ["Python", "SQL"]