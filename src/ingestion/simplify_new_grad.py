"""Fetch and normalize Simplify's public new-grad job index."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from src.processing.job_processor import categorize_role


DEFAULT_SIMPLIFY_NEW_GRAD_README_URL = (
    "https://raw.githubusercontent.com/"
    "SimplifyJobs/New-Grad-Positions/dev/README.md"
)
SIMPLIFY_SOURCE = "simplify_new_grad"
SOURCE_TYPE = "new_grad_index"

_ROW_START_PATTERN = re.compile(r"<tr(?:\s|>)", re.IGNORECASE)
_ROW_END_PATTERN = re.compile(r"</tr\s*>", re.IGNORECASE)
_SAME_COMPANY_MARKER = "\u21b3"
_BADGE_MARKERS = (
    "\U0001f393",  # advanced degree
    "\U0001f512",  # closed application
    "\U0001f525",  # highlighted company
    "\U0001f6c2",  # sponsorship badge
    "\ufe0f",
)
_REGIONAL_INDICATOR_PATTERN = re.compile("[\U0001f1e6-\U0001f1ff]")
_WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")
_LOCATION_BREAK_PATTERN = re.compile(r"\s*\n+\s*")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SimplifyNewGradPosting:
    company: str
    title: str
    location: str
    category: str
    listing_age: str
    apply_url: str
    company_url: str = ""
    simplify_url: str = ""


@dataclass(frozen=True)
class _HtmlCell:
    text: str
    links: tuple[str, ...]


class _SimplifyRowParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[_HtmlCell] = []
        self._in_cell = False
        self._cell_text: list[str] = []
        self._cell_links: list[str] = []
        self._skip_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag_name = tag.lower()

        if tag_name == "td":
            self._in_cell = True
            self._cell_text = []
            self._cell_links = []
            return

        if not self._in_cell:
            return

        if self._skip_depth:
            if tag_name not in {"br", "hr", "img", "input", "meta", "link"}:
                self._skip_depth += 1
            return

        if tag_name == "summary":
            self._skip_depth = 1
            return

        if tag_name in {"br", "p"}:
            self._cell_text.append("\n")
            return

        if tag_name == "a":
            attrs_dict = dict(attrs)
            href = str(attrs_dict.get("href") or "").strip()

            if href:
                self._cell_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()

        if tag_name == "br" and self._in_cell and not self._skip_depth:
            self._cell_text.append("\n")
            return

        if self._skip_depth:
            self._skip_depth -= 1
            return

        if tag_name == "td" and self._in_cell:
            self.cells.append(
                _HtmlCell(
                    text="".join(self._cell_text),
                    links=tuple(self._cell_links),
                )
            )
            self._in_cell = False
            self._cell_text = []
            self._cell_links = []

    def handle_data(self, data: str) -> None:
        if self._in_cell and not self._skip_depth:
            self._cell_text.append(data)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)


def fetch_simplify_new_grad_readme(
    readme_url: str = DEFAULT_SIMPLIFY_NEW_GRAD_README_URL,
    *,
    timeout_seconds: int = 20,
) -> str:
    """Fetch the Simplify new-grad README text."""
    response = requests.get(readme_url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.text


def fetch_simplify_new_grad_postings(
    readme_url: str = DEFAULT_SIMPLIFY_NEW_GRAD_README_URL,
    *,
    timeout_seconds: int = 20,
) -> list[SimplifyNewGradPosting]:
    """Fetch and parse active Simplify new-grad postings."""
    postings = parse_simplify_new_grad_readme(
        fetch_simplify_new_grad_readme(
            readme_url,
            timeout_seconds=timeout_seconds,
        )
    )

    if not postings:
        raise ValueError("Simplify new-grad source produced no active postings.")

    return postings


def parse_simplify_new_grad_readme(readme_text: str) -> list[SimplifyNewGradPosting]:
    """Parse active job rows from the Simplify new-grad README."""
    postings: list[SimplifyNewGradPosting] = []
    current_category = ""
    in_inactive_section = False
    in_row = False
    row_lines: list[str] = []
    last_company = ""
    last_company_url = ""

    for line in readme_text.splitlines():
        stripped_line = line.strip()

        if stripped_line.startswith("## "):
            current_category = _normalize_category_heading(stripped_line)
            in_inactive_section = False
            continue

        if "Inactive roles" in stripped_line:
            in_inactive_section = True
            continue

        if not current_category or in_inactive_section:
            continue

        if _ROW_START_PATTERN.search(stripped_line):
            in_row = True
            row_lines = [line]

            if _ROW_END_PATTERN.search(stripped_line):
                posting = _parse_posting_row(
                    "\n".join(row_lines),
                    category=current_category,
                    last_company=last_company,
                    last_company_url=last_company_url,
                )
                in_row = False

                if posting is not None:
                    postings.append(posting)
                    last_company = posting.company
                    last_company_url = posting.company_url
            continue

        if in_row:
            row_lines.append(line)

            if _ROW_END_PATTERN.search(stripped_line):
                posting = _parse_posting_row(
                    "\n".join(row_lines),
                    category=current_category,
                    last_company=last_company,
                    last_company_url=last_company_url,
                )
                in_row = False

                if posting is not None:
                    postings.append(posting)
                    last_company = posting.company
                    last_company_url = posting.company_url

    return postings


def normalize_simplify_new_grad_posting(
    posting: SimplifyNewGradPosting,
    *,
    fetched_at: datetime | str | None = None,
) -> dict[str, object]:
    """Return a JobLens-shaped raw job row for a Simplify new-grad posting."""
    fetched_datetime = _coerce_fetched_at(fetched_at)
    description = _build_index_description(posting)
    source_url = posting.apply_url or posting.simplify_url
    role_category = categorize_role(posting.title, description)

    return {
        "job_id": _build_simplify_job_id(posting),
        "title": posting.title,
        "company": posting.company,
        "location": posting.location,
        "description": description,
        "experience_level": "Entry Level",
        "source": SIMPLIFY_SOURCE,
        "source_url": source_url,
        "fetched_at": fetched_datetime.isoformat(),
        "date_posted": _date_posted_from_age(
            posting.listing_age,
            fetched_at=fetched_datetime,
        ),
        "valid_through": "",
        "employment_type": "Full-time",
        "workplace_type": "Remote"
        if "remote" in posting.location.lower()
        else "",
        "is_remote": "remote" in posting.location.lower(),
        "address_locality": "",
        "address_region": "",
        "address_country": "",
        "original_location": posting.location,
        "city": "",
        "province": "",
        "country": "",
        "role_category": role_category,
        "source_updated_at": posting.listing_age,
        "description_formatted": description,
        "source_type": SOURCE_TYPE,
        "apply_url": posting.apply_url,
        "source_record_url": posting.simplify_url,
        "company_url": posting.company_url,
        "new_grad_category": posting.category,
        "early_career_signal": "new_grad",
        "seniority_signal": "entry_level",
    }


def normalize_simplify_new_grad_postings(
    postings: list[SimplifyNewGradPosting],
    *,
    fetched_at: datetime | str | None = None,
) -> list[dict[str, object]]:
    """Normalize multiple Simplify new-grad postings with one fetch timestamp."""
    fetched_datetime = _coerce_fetched_at(fetched_at)

    return [
        normalize_simplify_new_grad_posting(
            posting,
            fetched_at=fetched_datetime,
        )
        for posting in postings
    ]


def _parse_posting_row(
    row_html: str,
    *,
    category: str,
    last_company: str,
    last_company_url: str,
) -> SimplifyNewGradPosting | None:
    parser = _SimplifyRowParser()
    parser.feed(row_html)
    cells = parser.cells

    if len(cells) != 5:
        return None

    if "\U0001f512" in row_html:
        return None

    raw_company = _normalize_display_text(cells[0].text)
    same_company = _is_same_company_cell(cells[0].text)
    company = last_company if same_company else raw_company
    company_url = (
        last_company_url
        if same_company
        else _first_matching_link(cells[0].links)
    )
    title = _normalize_display_text(cells[1].text)
    location = _normalize_location_text(cells[2].text)
    apply_url = _select_apply_url(cells[3].links)
    simplify_url = _first_matching_link(
        cells[3].links,
        host_suffix="simplify.jobs",
    )
    listing_age = _normalize_display_text(cells[4].text)

    if not company or not title or not location or not (apply_url or simplify_url):
        return None

    return SimplifyNewGradPosting(
        company=company,
        title=title,
        location=location,
        category=category,
        listing_age=listing_age,
        apply_url=apply_url,
        company_url=company_url,
        simplify_url=simplify_url,
    )


def _normalize_category_heading(line: str) -> str:
    text = line.lstrip("#").strip()
    text = _normalize_display_text(text)
    text = re.sub(r"^[^\w]+", "", text).strip()
    text = re.sub(r"\s+New Grad Roles.*$", "", text, flags=re.IGNORECASE)
    return text.strip()


def _normalize_display_text(value: object) -> str:
    text = unescape(str(value or "")).replace("\xa0", " ")

    for marker in _BADGE_MARKERS:
        text = text.replace(marker, "")

    text = _REGIONAL_INDICATOR_PATTERN.sub("", text)
    text = text.replace(_SAME_COMPANY_MARKER, "")
    text = _LOCATION_BREAK_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)

    return text.strip(" -|")


def _normalize_location_text(value: object) -> str:
    text = unescape(str(value or "")).replace("\xa0", " ")

    for marker in _BADGE_MARKERS:
        text = text.replace(marker, "")

    text = _REGIONAL_INDICATOR_PATTERN.sub("", text)
    text = _LOCATION_BREAK_PATTERN.sub("; ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text)

    return text.strip(" ;")


def _is_same_company_cell(value: object) -> bool:
    return _SAME_COMPANY_MARKER in str(value or "")


def _first_matching_link(
    links: tuple[str, ...],
    *,
    host_suffix: str | None = None,
) -> str:
    for link in links:
        if not host_suffix:
            return link

        if urlparse(link).netloc.lower().endswith(host_suffix):
            return link

    return ""


def _select_apply_url(links: tuple[str, ...]) -> str:
    for link in links:
        if not urlparse(link).netloc.lower().endswith("simplify.jobs"):
            return link

    return _first_matching_link(links)


def _coerce_fetched_at(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    if isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)

    return datetime.now(UTC)


def _date_posted_from_age(age: str, *, fetched_at: datetime) -> str:
    days_old = _parse_age_to_days(age)

    if days_old is None:
        return ""

    return (fetched_at - timedelta(days=days_old)).date().isoformat()


def _parse_age_to_days(age: str) -> int | None:
    match = re.fullmatch(r"\s*(\d+)\s*(h|d|w|mo|m|y)\s*", age.lower())

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "h":
        return 0

    if unit == "d":
        return amount

    if unit == "w":
        return amount * 7

    if unit in {"mo", "m"}:
        return amount * 30

    if unit == "y":
        return amount * 365

    return None


def _build_simplify_job_id(posting: SimplifyNewGradPosting) -> str:
    stable_value = (
        posting.simplify_url
        or posting.apply_url
        or f"{posting.company}|{posting.title}|{posting.location}"
    )
    digest = hashlib.sha256(stable_value.encode("utf-8")).hexdigest()[:12]
    company_slug = _slugify(posting.company)

    return f"{SIMPLIFY_SOURCE}:{company_slug}:{digest}"


def _slugify(value: str) -> str:
    slug = _SLUG_PATTERN.sub("-", value.lower()).strip("-")
    return slug or "unknown"


def _build_index_description(posting: SimplifyNewGradPosting) -> str:
    details = [
        "New-grad job listing from SimplifyJobs/New-Grad-Positions.",
        f"Role: {posting.title}.",
        f"Company: {posting.company}.",
        f"Category: {posting.category}.",
        f"Location: {posting.location}.",
    ]

    if posting.listing_age:
        details.append(f"Listing age: {posting.listing_age}.")

    if posting.apply_url:
        details.append(f"Apply URL: {posting.apply_url}.")

    return "\n".join(details)
