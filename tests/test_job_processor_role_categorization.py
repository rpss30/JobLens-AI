from src.processing.job_processor import categorize_role


def test_categorize_role_handles_real_job_title_variants():
    assert categorize_role("Applied Scientist", "") == "AI/ML"
    assert categorize_role("Analytics Engineer", "") == "Data Engineering"
    assert categorize_role("Site Reliability Engineer", "") == "Cloud/AWS"
    assert categorize_role("Infrastructure Engineer", "") == "Cloud/AWS"
