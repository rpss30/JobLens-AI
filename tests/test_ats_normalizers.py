from src.ingestion.ats_normalizers import (
    build_ats_job_id,
    clean_html_text,
    epoch_milliseconds_to_iso,
    infer_experience_level_from_text,
)


def test_clean_html_text_removes_tags_entities_and_extra_whitespace():
    html = "<p>Build&nbsp;APIs</p><ul><li>Python</li><li>SQL</li></ul>"

    assert clean_html_text(html) == "Build APIs Python SQL"


def test_clean_html_text_handles_none():
    assert clean_html_text(None) == ""


def test_build_ats_job_id_includes_source_company_and_posting_id():
    assert build_ats_job_id("Lever", "SomeCompany", "abc123") == "lever:somecompany:abc123"


def test_epoch_milliseconds_to_iso_converts_lever_timestamp():
    assert epoch_milliseconds_to_iso(0) == "1970-01-01T00:00:00+00:00"
    assert epoch_milliseconds_to_iso("not-a-timestamp") == ""


def test_infer_experience_level_detects_senior_roles():
    assert infer_experience_level_from_text("Senior ML Engineer", "") == "Senior"


def test_infer_experience_level_detects_entry_level_roles():
    assert infer_experience_level_from_text(
        "Software Engineer",
        "This role is ideal for a new graduate or entry-level candidate.",
    ) == "Entry Level"


def test_infer_experience_level_defaults_to_mid_level():
    assert infer_experience_level_from_text("Data Engineer", "Build data pipelines.") == "Mid Level"


def test_infer_experience_level_does_not_use_generic_description_senior_terms():
    assert infer_experience_level_from_text(
        "Software Engineer",
        "Partner with the engineering manager and demonstrate leadership.",
    ) == "Mid Level"


def test_infer_experience_level_ignores_generic_graduate_description_text():
    assert infer_experience_level_from_text(
        "Software Engineer",
        "Applicants may have graduate education or equivalent experience.",
    ) == "Mid Level"


def test_infer_experience_level_uses_required_years():
    assert infer_experience_level_from_text(
        "Software Engineer",
        "Requires 1+ years of Python experience.",
    ) == "Entry Level"
    assert infer_experience_level_from_text(
        "Software Engineer",
        "Requires 5+ years of Python experience.",
    ) == "Senior"
