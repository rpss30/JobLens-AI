from src.ingestion.ats_normalizers import (
    clean_html_document,
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


def test_clean_html_document_keeps_paragraphs_and_lists() -> None:
    text = clean_html_document(
        "<p>About the role</p><p>We ship weekly.</p><ul><li>Go</li><li>SQL</li></ul>"
    )

    assert text == "About the role\n\nWe ship weekly.\n\n- Go\n- SQL"


def test_clean_html_document_reads_escaped_markup() -> None:
    """Greenhouse sends its body as escaped HTML.

    Stripping tags before decoding entities left every tag standing in the
    text, because there were no tags to strip until the entities were read.
    """
    text = clean_html_document(
        "&lt;p&gt;&lt;strong&gt;About Faire&lt;/strong&gt;&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Go&lt;/li&gt;&lt;/ul&gt;"
    )

    assert "<" not in text
    assert text == "About Faire\n\n- Go"


def test_clean_html_document_reads_doubly_escaped_markup() -> None:
    """Greenhouse escapes its body twice, so one pass is not enough.

    A single decode turned &amp;amp;nbsp; into a visible &nbsp; rather than a
    space.
    """
    text = clean_html_document(
        "&amp;lt;p&amp;gt;Tools &amp;amp;nbsp;and teams&amp;lt;/p&amp;gt;"
    )

    assert "&" not in text
    assert "<" not in text
    assert text == "Tools and teams"


def test_clean_html_text_still_flattens_a_title() -> None:
    """The sibling used for titles and locations is deliberately unchanged."""
    assert clean_html_text("  Senior   Engineer\n(Remote)  ") == "Senior Engineer (Remote)"
