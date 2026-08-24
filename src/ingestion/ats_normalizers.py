"""Normalizers for ATS-sourced job postings from Lever and Greenhouse."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from html import unescape


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Tags that close a block of prose, where a paragraph break belongs.
_PARAGRAPH_END_PATTERN = re.compile(
    r"(?i)</(?:p|div|h[1-6]|ul|ol|section|article|tr|blockquote)\s*>"
)
# A line break within a block.
_LINE_BREAK_PATTERN = re.compile(r"(?i)<br\s*/?>")
# An item opens its own line; its closing tag adds nothing, or every list
# would come out double spaced.
_LIST_ITEM_PATTERN = re.compile(r"(?i)<li[^>]*>")
_LIST_ITEM_END_PATTERN = re.compile(r"(?i)</li\s*>")
# Spaces and tabs, but not newlines: the newlines are the point.
_HORIZONTAL_SPACE_PATTERN = re.compile(r"[^\S\n]+")
_EXCESS_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")

# Enough for the double encoding seen in the wild, and a stop either way.
MAX_UNESCAPE_PASSES = 3


def clean_html_text(value: object) -> str:
    """Convert simple HTML/text content into readable plain text."""
    if value is None:
        return ""

    text = str(value)
    text = _HTML_TAG_PATTERN.sub(" ", text)
    text = unescape(text)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()


def clean_html_document(value: object) -> str:
    """Convert a posting body to plain text, keeping its paragraphs and lists.

    The sibling of clean_html_text, and deliberately separate from it: that
    one flattens every run of whitespace to a single space, which is right for
    a title or a location and ruinous for a description. Boards hand us either
    HTML or plain text that already carries newlines, and both keep their
    shape here.
    """
    if value is None:
        return ""

    text = str(value)

    # Entities first. Greenhouse sends its body as escaped HTML, so the tags
    # only become tags once this runs; stripping before it would leave every
    # <p> and <li> standing in the text as visible characters. It escapes
    # twice, so &amp;nbsp; needs a second pass, and the loop stops as soon as
    # a pass changes nothing rather than assuming a fixed depth.
    for _ in range(MAX_UNESCAPE_PASSES):
        decoded = unescape(text)

        if decoded == text:
            break

        text = decoded

    text = _LIST_ITEM_END_PATTERN.sub("", text)
    text = _LIST_ITEM_PATTERN.sub("\n- ", text)
    text = _LINE_BREAK_PATTERN.sub("\n", text)
    text = _PARAGRAPH_END_PATTERN.sub("\n\n", text)
    # Whatever is left is inline markup, which leaves no gap when it goes.
    text = _HTML_TAG_PATTERN.sub("", text)

    text = _HORIZONTAL_SPACE_PATTERN.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _EXCESS_BLANK_LINES_PATTERN.sub("\n\n", text)

    return text.strip()


def build_ats_job_id(source: str, company_slug: str, posting_id: object) -> str:
    """Build a stable source-aware job id for ATS postings."""
    cleaned_source = str(source).strip().lower()
    cleaned_company = str(company_slug).strip().lower()
    cleaned_posting_id = str(posting_id).strip()

    return f"{cleaned_source}:{cleaned_company}:{cleaned_posting_id}"


def current_utc_timestamp() -> str:
    """Return an ISO timestamp for ingestion output."""
    return datetime.now(UTC).isoformat()


def epoch_milliseconds_to_iso(value: object) -> str:
    """Convert an epoch-millisecond value to an ISO UTC timestamp."""
    if value is None or value == "":
        return ""

    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return ""

    return datetime.fromtimestamp(
        milliseconds / 1000,
        tz=UTC,
    ).isoformat()


def infer_experience_level_from_text(title: object, description: object) -> str:
    """Infer a simple experience level label from title and description text."""
    title_text = str(title or "").lower()
    description_text = str(description or "").lower()

    senior_terms = [
        "senior",
        "sr.",
        "staff",
        "principal",
        "lead",
        "manager",
        "director",
    ]
    entry_terms = [
        "junior",
        "jr.",
        "entry level",
        "entry-level",
        "new grad",
        "new graduate",
        "graduate",
        "intern",
        "internship",
        "co-op",
        "coop",
    ]
    description_entry_terms = [
        "entry level",
        "entry-level",
        "new grad",
        "new graduate",
        "recent graduate",
    ]

    if any(term in title_text for term in senior_terms):
        return "Senior"

    if any(term in title_text for term in entry_terms):
        return "Entry Level"

    if any(term in description_text for term in description_entry_terms):
        return "Entry Level"

    years_of_experience = [
        int(match)
        for match in re.findall(
            r"(?<!\d)(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\+?\s*(?:years?|yrs?)",
            description_text,
        )
    ]

    if years_of_experience:
        minimum_years = min(years_of_experience)

        if minimum_years >= 5:
            return "Senior"

        if minimum_years <= 2:
            return "Entry Level"

    return "Mid Level"
