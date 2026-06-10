from src.skill_extraction.normalizer import normalize_skill_list, normalize_skill_name


def test_normalize_skill_name_lowercases_and_trims_whitespace():
    assert normalize_skill_name("  Python  ") == "python"
    assert normalize_skill_name("  Machine Learning  ") == "machine learning"


def test_normalize_skill_name_replaces_separators_with_spaces():
    assert normalize_skill_name("CI/CD") == "ci cd"
    assert normalize_skill_name("React|Next.js") == "react next.js"
    assert normalize_skill_name("Python; SQL") == "python sql"


def test_normalize_skill_list_removes_empty_non_string_and_duplicate_values():
    skills = [
        " Python ",
        "",
        "python",
        "SQL",
        None,
        "  ",
        "Machine Learning",
    ]

    assert normalize_skill_list(skills) == ["python", "sql", "machine learning"]


def test_normalize_skill_list_respects_max_skills_limit():
    skills = ["Python", "SQL", "AWS", "Docker"]

    assert normalize_skill_list(skills, max_skills=2) == ["python", "sql"]