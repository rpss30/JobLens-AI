from scripts.process_greenhouse_jobs import REQUIRED_COLUMNS


def test_process_greenhouse_required_columns_match_raw_processing_schema():
    assert REQUIRED_COLUMNS == [
        "job_id",
        "title",
        "company",
        "location",
        "description",
        "experience_level",
    ]