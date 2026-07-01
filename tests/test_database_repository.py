# tests/test_database_repository.py

from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from src.database import repository
from src.database.models import Dataset, JobPosting, JobSkill, ProcessedJob, Skill
from src.database.repository import (
    build_analysis_run_name,
    clean_optional_bool,
    clean_optional_string,
    dataset_name_exists,
    build_uploaded_dataset_name,
    is_user_managed_dataset,
    normalize_skill_name,
    parse_optional_datetime,
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


class FakeSeedSession:
    def __init__(self):
        self.added = []
        self.statements = []
        self.flushed = False
        self._next_id = 1

    def execute(self, statement):
        self.statements.append(statement)
        return FakeScalarResult(None)

    def add(self, value):
        if getattr(value, "id", None) is None:
            value.id = self._next_id
            self._next_id += 1

        self.added.append(value)

    def flush(self):
        self.flushed = True


def patch_db_session(monkeypatch, fake_session):
    @contextmanager
    def fake_db_session():
        yield fake_session

    monkeypatch.setattr(repository, "get_db_session", fake_db_session)


def test_normalize_skill_name_lowercases_and_strips_whitespace():
    assert normalize_skill_name("  Python  ") == "python"


def test_clean_optional_string_preserves_database_nulls():
    assert clean_optional_string("  https://example.com/job  ") == "https://example.com/job"
    assert clean_optional_string("   ") is None
    assert clean_optional_string(None) is None
    assert clean_optional_string(float("nan")) is None


def test_clean_optional_bool_parses_common_csv_values():
    assert clean_optional_bool(True) is True
    assert clean_optional_bool("true") is True
    assert clean_optional_bool("1") is True
    assert clean_optional_bool("false") is False
    assert clean_optional_bool("") is False
    assert clean_optional_bool(None) is False


def test_parse_optional_datetime_returns_utc_datetime():
    parsed_value = parse_optional_datetime("2026-06-21T12:00:00Z")

    assert parsed_value == datetime(2026, 6, 21, 12, tzinfo=UTC)
    assert parse_optional_datetime("") is None


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


def test_save_uploaded_dataset_requires_custom_name():
    with pytest.raises(ValueError, match="Dataset name is required"):
        repository.save_uploaded_dataset_from_dataframe(
            df=pd.DataFrame(),
            filename="Sample Jobs Upload.csv",
            custom_name="   ",
        )

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


def test_seed_processed_jobs_preserves_source_and_extraction_metadata(monkeypatch):
    fake_session = FakeSeedSession()
    patch_db_session(monkeypatch, fake_session)

    df = pd.DataFrame(
        [
            {
                "job_id": " greenhouse:test:123 ",
                "title": "Backend Engineer",
                "company": "Example",
                "location": "Toronto, ON",
                "description": "Build APIs with Python and PostgreSQL.",
                "experience_level": "Entry Level",
                "source": "greenhouse",
                "source_url": " https://example.com/jobs/123 ",
                "fetched_at": "2026-06-21T12:00:00Z",
                "is_remote": "false",
                "clean_title": "backend engineer",
                "clean_description": "build apis with python and postgresql",
                "extracted_skills": ["Python", "PostgreSQL"],
                "role_category": "Software Engineering",
                "skills_text": "Python, PostgreSQL",
                "skill_extraction_provider": "groq",
                "skill_extraction_error": "",
            }
        ]
    )

    inserted_count = repository.seed_processed_jobs_from_dataframe(
        df=df,
        dataset_name="canada_jobs",
        source_type="canada_snapshot",
        replace_existing=False,
    )

    assert inserted_count == 1

    dataset = next(item for item in fake_session.added if isinstance(item, Dataset))
    job_posting = next(
        item for item in fake_session.added if isinstance(item, JobPosting)
    )
    processed_job = next(
        item for item in fake_session.added if isinstance(item, ProcessedJob)
    )
    skills = [item for item in fake_session.added if isinstance(item, Skill)]
    job_skills = [
        item for item in fake_session.added if isinstance(item, JobSkill)
    ]

    assert dataset.name == "canada_jobs"
    assert dataset.source_type == "canada_snapshot"
    assert job_posting.job_id == "greenhouse:test:123"
    assert job_posting.source == "greenhouse"
    assert job_posting.source_url == "https://example.com/jobs/123"
    assert job_posting.fetched_at == datetime(2026, 6, 21, 12, tzinfo=UTC)
    assert job_posting.is_remote is False
    assert processed_job.skill_extraction_provider == "groq"
    assert processed_job.skill_extraction_error is None
    assert [skill.normalized_name for skill in skills] == ["python", "postgresql"]
    assert len(job_skills) == 2


def test_seed_processed_jobs_converts_blank_optional_ids_to_null(monkeypatch):
    fake_session = FakeSeedSession()
    patch_db_session(monkeypatch, fake_session)

    df = pd.DataFrame(
        [
            {
                "job_id": " ",
                "title": "Data Analyst",
                "company": "Example",
                "location": "Remote, Canada",
                "description": "Analyze data with SQL.",
                "experience_level": "Entry Level",
                "source_url": "",
                "clean_title": "data analyst",
                "clean_description": "analyze data with sql",
                "extracted_skills": ["SQL"],
                "role_category": "Analytics",
                "skills_text": "SQL",
            }
        ]
    )

    repository.seed_processed_jobs_from_dataframe(
        df=df,
        dataset_name="uploaded_jobs",
        source_type="uploaded_csv",
        replace_existing=False,
    )

    job_posting = next(
        item for item in fake_session.added if isinstance(item, JobPosting)
    )

    assert job_posting.job_id is None
    assert job_posting.source_url is None
