from scripts.fetch_greenhouse_jobs import OUTPUT_COLUMNS, is_target_job


def test_greenhouse_script_output_columns_match_raw_schema_plus_target_flag():
    assert OUTPUT_COLUMNS == [
        "job_id",
        "title",
        "company",
        "location",
        "description",
        "experience_level",
        "source",
        "source_url",
        "fetched_at",
        "is_target_job",
    ]


def test_is_target_job_matches_relevant_ai_data_cloud_backend_roles():
    job = {
        "title": "Machine Learning Engineer",
        "description": "Build ML systems with Python, AWS, and data pipelines.",
    }

    assert is_target_job(job) is True


def test_is_target_job_rejects_unrelated_roles():
    job = {
        "title": "Legal Counsel",
        "description": "Draft contracts and advise business teams.",
    }

    assert is_target_job(job) is False