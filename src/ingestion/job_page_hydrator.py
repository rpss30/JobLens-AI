"""Best-effort text extraction for public job application pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser

import requests


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; JobLensBot/1.0; +https://joblens.local)"
)
DEFAULT_MIN_TEXT_CHARS = 500
DEFAULT_MAX_TEXT_CHARS = 12_000

_BLOCK_TAGS = {
    "article",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "p",
    "section",
    "tr",
}
_SKIP_TAGS = {
    "footer",
    "form",
    "head",
    "header",
    "iframe",
    "nav",
    "noscript",
    "script",
    "style",
    "svg",
}
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class JobPageHydrationResult:
    description: str
    provider: str
    status_code: int | None = None
    error: str = ""


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_body = False
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag_name = tag.lower()

        if tag_name == "body":
            self._in_body = True

        if not self._in_body:
            return

        if self._skip_depth:
            if tag_name not in _VOID_TAGS:
                self._skip_depth += 1
            return

        if tag_name in _SKIP_TAGS:
            self._skip_depth = 1
            return

        if tag_name in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()

        if self._skip_depth:
            self._skip_depth -= 1
            return

        if self._in_body and tag_name in _BLOCK_TAGS:
            self._parts.append("\n")

        if tag_name == "body":
            self._in_body = False

    def handle_data(self, data: str) -> None:
        if self._in_body and not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def extract_visible_job_text(
    html: str,
    *,
    max_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> str:
    """Extract readable body text from a generic application page."""
    parser = _VisibleTextParser()
    parser.feed(html)
    text = unescape(parser.text()).replace("\xa0", " ")
    lines: list[str] = []

    for raw_line in text.splitlines():
        line = _WHITESPACE_PATTERN.sub(" ", raw_line).strip()

        if not line or _is_boilerplate_line(line):
            continue

        lines.append(line)

    cleaned_text = _BLANK_LINES_PATTERN.sub("\n\n", "\n".join(lines)).strip()
    return cleaned_text[:max_chars].strip()


def hydrate_job_page(
    url: str,
    *,
    timeout_seconds: int = 15,
    min_text_chars: int = DEFAULT_MIN_TEXT_CHARS,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> JobPageHydrationResult:
    """Fetch a public application page and return useful visible text if present."""
    cleaned_url = str(url or "").strip()

    if not cleaned_url:
        return JobPageHydrationResult(
            description="",
            provider="source_index_fallback",
            error="missing source URL",
        )

    try:
        response = requests.get(
            cleaned_url,
            timeout=timeout_seconds,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as error:
        status_code = getattr(getattr(error, "response", None), "status_code", None)
        return JobPageHydrationResult(
            description="",
            provider="source_index_fallback",
            status_code=status_code,
            error=f"{type(error).__name__}: {error}",
        )

    description = extract_visible_job_text(
        response.text,
        max_chars=max_text_chars,
    )

    if len(description) < min_text_chars:
        return JobPageHydrationResult(
            description="",
            provider="source_index_fallback",
            status_code=response.status_code,
            error=(
                "application page did not expose enough static job text "
                f"({len(description)} chars)"
            ),
        )

    return JobPageHydrationResult(
        description=description,
        provider="apply_page",
        status_code=response.status_code,
    )


def _is_boilerplate_line(line: str) -> bool:
    lowered = line.casefold()
    boilerplate = {
        "apply",
        "back to jobs",
        "job application",
        "search again",
        "skip to main content",
    }

    if lowered in boilerplate:
        return True

    if lowered.startswith("please enable cookies") and len(line) < 90:
        return True

    if lowered.startswith("enable javascript") and len(line) < 90:
        return True

    return False
