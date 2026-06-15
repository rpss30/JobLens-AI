# tests/test_database_repository.py

from src.database.repository import (
    build_analysis_run_name,
    build_uploaded_dataset_name,
    is_user_managed_dataset,
    normalize_skill_name,
    parse_skills,
    slugify_dataset_name,
)


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

def test_slugify_dataset_name_lowercases_and_replaces_special_characters():
    assert slugify_dataset_name("My Jobs Upload.csv") == "my_jobs_upload_csv"


def test_slugify_dataset_name_handles_empty_input():
    assert slugify_dataset_name("   ") == "uploaded_dataset"


def test_build_uploaded_dataset_name_uses_uploaded_prefix_and_file_stem():
    dataset_name = build_uploaded_dataset_name("Sample Jobs Upload.csv")

    assert dataset_name.startswith("uploaded_")
    assert dataset_name.endswith("_sample_jobs_upload")

def test_build_analysis_run_name_includes_role_and_dataset_name():
    result = build_analysis_run_name(
        best_role="Cloud/AWS",
        dataset_name="sample_jobs",
    )

    assert result.startswith("analysis_")
    assert "cloud_aws" in result
    assert "sample_jobs" in result


def test_build_analysis_run_name_handles_missing_best_role():
    result = build_analysis_run_name(
        best_role=None,
        dataset_name="Uploaded Jobs.csv",
    )

    assert result.startswith("analysis_")
    assert "uploaded_jobs_csv" in result

def test_is_user_managed_dataset_allows_uploaded_csv():
    assert is_user_managed_dataset("uploaded_csv") is True


def test_is_user_managed_dataset_protects_sample_csv():
    assert is_user_managed_dataset("sample_csv") is False