from src.ingestion.ats_normalizers import (
    build_ats_job_id,
    clean_html_text,
    infer_experience_level_from_text,
)


def test_clean_html_text_removes_tags_entities_and_extra_whitespace():
    html = "<p>Build&nbsp;APIs</p><ul><li>Python</li><li>SQL</li></ul>"

    assert clean_html_text(html) == "Build APIs Python SQL"


def test_clean_html_text_handles_none():
    assert clean_html_text(None) == ""


def test_build_ats_job_id_includes_source_company_and_posting_id():
    assert build_ats_job_id("Lever", "SomeCompany", "abc123") == "lever:somecompany:abc123"


def test_infer_experience_level_detects_senior_roles():
    assert infer_experience_level_from_text("Senior ML Engineer", "") == "Senior"


def test_infer_experience_level_detects_entry_level_roles():
    assert infer_experience_level_from_text(
        "Software Engineer",
        "This role is ideal for a new graduate or entry-level candidate.",
    ) == "Entry Level"


def test_infer_experience_level_defaults_to_mid_level():
    assert infer_experience_level_from_text("Data Engineer", "Build data pipelines.") == "Mid Level"