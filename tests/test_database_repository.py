# tests/test_database_repository.py

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from src.database import repository
from src.database.repository import (
    build_analysis_run_name,
    dataset_name_exists,
    build_uploaded_dataset_name,
    is_user_managed_dataset,
    normalize_skill_name,
    parse_skills,
    slugify_dataset_name,
)


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, scalar_results):
        self.scalar_results = list(scalar_results)
        self.flushed = False
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return FakeScalarResult(self.scalar_results.pop(0))

    def flush(self):
        self.flushed = True


def patch_db_session(monkeypatch, fake_session):
    @contextmanager
    def fake_db_session():
        yield fake_session

    monkeypatch.setattr(repository, "get_db_session", fake_db_session)


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

def test_build_uploaded_dataset_name_uses_custom_dataset_name():
    dataset_name = build_uploaded_dataset_name(
        filename="Sample Jobs Upload.csv",
        custom_name="My Portfolio Jobs!",
    )

    assert dataset_name == "my_portfolio_jobs"


def test_build_uploaded_dataset_name_falls_back_when_custom_name_is_blank():
    dataset_name = build_uploaded_dataset_name(
        filename="Sample Jobs Upload.csv",
        custom_name="   ",
    )

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


def test_dataset_name_exists_returns_true_when_dataset_is_found(monkeypatch):
    fake_session = FakeSession([1])
    patch_db_session(monkeypatch, fake_session)

    assert dataset_name_exists("uploaded_jobs") is True


def test_dataset_name_exists_returns_false_when_dataset_is_missing(monkeypatch):
    fake_session = FakeSession([None])
    patch_db_session(monkeypatch, fake_session)

    assert dataset_name_exists("missing_dataset") is False


def test_rename_dataset_renames_uploaded_dataset_and_analysis_runs(monkeypatch):
    analysis_run = SimpleNamespace(dataset_name="uploaded_jobs")
    dataset = SimpleNamespace(
        id=1,
        name="uploaded_jobs",
        source_type="uploaded_csv",
        analysis_runs=[analysis_run],
    )
    fake_session = FakeSession([dataset, None])
    patch_db_session(monkeypatch, fake_session)

    renamed = repository.rename_dataset("uploaded_jobs", "My Custom Dataset")

    assert renamed is True
    assert dataset.name == "my_custom_dataset"
    assert analysis_run.dataset_name == "my_custom_dataset"
    assert fake_session.flushed is True


def test_rename_dataset_returns_false_when_dataset_is_missing(monkeypatch):
    fake_session = FakeSession([None])
    patch_db_session(monkeypatch, fake_session)

    assert repository.rename_dataset("missing_dataset", "new_name") is False


def test_rename_dataset_rejects_protected_sample_dataset(monkeypatch):
    dataset = SimpleNamespace(
        id=1,
        name="sample_jobs",
        source_type="sample_csv",
        analysis_runs=[],
    )
    fake_session = FakeSession([dataset])
    patch_db_session(monkeypatch, fake_session)

    with pytest.raises(ValueError, match="Only uploaded CSV datasets can be renamed"):
        repository.rename_dataset("sample_jobs", "renamed_sample")


def test_rename_dataset_rejects_duplicate_target_name(monkeypatch):
    dataset = SimpleNamespace(
        id=1,
        name="uploaded_jobs",
        source_type="uploaded_csv",
        analysis_runs=[],
    )
    duplicate_dataset = SimpleNamespace(
        id=2,
        name="existing_dataset",
        source_type="uploaded_csv",
        analysis_runs=[],
    )
    fake_session = FakeSession([dataset, duplicate_dataset])
    patch_db_session(monkeypatch, fake_session)

    with pytest.raises(ValueError, match="already exists"):
        repository.rename_dataset("uploaded_jobs", "Existing Dataset")
