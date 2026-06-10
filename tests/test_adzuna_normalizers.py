from src.ingestion.normalizers import (
    infer_experience_level,
    normalize_adzuna_job,
    normalize_adzuna_jobs,
)


def test_infer_experience_level_detects_entry_level_keywords():
    assert infer_experience_level("Junior Data Scientist", "Work with Python and SQL") == "Entry Level"
    assert infer_experience_level("Machine Learning Intern", "Build ML models") == "Entry Level"
    assert infer_experience_level("Software Engineer", "New grad role") == "Entry Level"


def test_infer_experience_level_detects_senior_keywords():
    assert infer_experience_level("Senior Machine Learning Engineer", "Build models") == "Senior"
    assert infer_experience_level("Lead Data Engineer", "Own pipelines") == "Senior"


def test_infer_experience_level_defaults_to_mid_level():
    assert infer_experience_level("Data Analyst", "Build dashboards with SQL") == "Mid Level"


def test_normalize_adzuna_job_maps_expected_fields():
    raw_job = {
        "id": "abc123",
        "title": "Data Scientist",
        "description": "Use Python, SQL, and statistics to build models.",
        "company": {"display_name": "Example Analytics"},
        "location": {"display_name": "Toronto, Ontario"},
        "redirect_url": "https://example.com/job/abc123",
    }

    normalized = normalize_adzuna_job(raw_job)

    assert normalized["job_id"] == "abc123"
    assert normalized["title"] == "Data Scientist"
    assert normalized["company"] == "Example Analytics"
    assert normalized["location"] == "Toronto, Ontario"
    assert normalized["description"] == "Use Python, SQL, and statistics to build models."
    assert normalized["experience_level"] == "Mid Level"
    assert normalized["source"] == "adzuna"
    assert normalized["source_url"] == "https://example.com/job/abc123"
    assert normalized["fetched_at"]


def test_normalize_adzuna_jobs_filters_incomplete_jobs():
    raw_jobs = [
        {
            "id": "valid-1",
            "title": "Backend Developer",
            "description": "Build REST APIs with Python.",
            "company": {"display_name": "Example Tech"},
            "location": {"display_name": "Vancouver, BC"},
            "redirect_url": "https://example.com/job/valid-1",
        },
        {
            "id": "missing-description",
            "title": "Data Analyst",
            "description": "",
            "company": {"display_name": "Example Analytics"},
            "location": {"display_name": "Toronto, Ontario"},
        },
    ]

    normalized_jobs = normalize_adzuna_jobs(raw_jobs)

    assert len(normalized_jobs) == 1
    assert normalized_jobs[0]["job_id"] == "valid-1"