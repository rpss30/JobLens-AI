"""Canadian location detection and normalization for job postings."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


PROVINCE_NAMES = {
    "alberta": "AB",
    "british columbia": "BC",
    "manitoba": "MB",
    "new brunswick": "NB",
    "newfoundland and labrador": "NL",
    "newfoundland": "NL",
    "northwest territories": "NT",
    "nova scotia": "NS",
    "nunavut": "NU",
    "ontario": "ON",
    "prince edward island": "PE",
    "quebec": "QC",
    "saskatchewan": "SK",
    "yukon": "YT",
}

PROVINCE_LABELS = {
    "AB": "Alberta",
    "BC": "British Columbia",
    "MB": "Manitoba",
    "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador",
    "NT": "Northwest Territories",
    "NS": "Nova Scotia",
    "NU": "Nunavut",
    "ON": "Ontario",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "SK": "Saskatchewan",
    "YT": "Yukon",
}

CITY_PROVINCES = {
    "barrie": ("Barrie", "ON"),
    "brampton": ("Brampton", "ON"),
    "burnaby": ("Burnaby", "BC"),
    "calgary": ("Calgary", "AB"),
    "charlottetown": ("Charlottetown", "PE"),
    "edmonton": ("Edmonton", "AB"),
    "fredericton": ("Fredericton", "NB"),
    "gatineau": ("Gatineau", "QC"),
    "greater toronto area": ("Toronto", "ON"),
    "gta": ("Toronto", "ON"),
    "halifax": ("Halifax", "NS"),
    "hamilton": ("Hamilton", "ON"),
    "iqaluit": ("Iqaluit", "NU"),
    "kelowna": ("Kelowna", "BC"),
    "kitchener": ("Kitchener", "ON"),
    "laval": ("Laval", "QC"),
    "london": ("London", "ON"),
    "markham": ("Markham", "ON"),
    "mississauga": ("Mississauga", "ON"),
    "moncton": ("Moncton", "NB"),
    "montreal": ("Montreal", "QC"),
    "north york": ("North York", "ON"),
    "oakville": ("Oakville", "ON"),
    "oshawa": ("Oshawa", "ON"),
    "ottawa": ("Ottawa", "ON"),
    "quebec city": ("Quebec City", "QC"),
    "regina": ("Regina", "SK"),
    "richmond": ("Richmond", "BC"),
    "saskatoon": ("Saskatoon", "SK"),
    "scarborough": ("Scarborough", "ON"),
    "st johns": ("St. John's", "NL"),
    "st. john's": ("St. John's", "NL"),
    "surrey": ("Surrey", "BC"),
    "toronto": ("Toronto", "ON"),
    "vancouver": ("Vancouver", "BC"),
    "victoria": ("Victoria", "BC"),
    "waterloo": ("Waterloo", "ON"),
    "whitehorse": ("Whitehorse", "YT"),
    "winnipeg": ("Winnipeg", "MB"),
    "yellowknife": ("Yellowknife", "NT"),
}

CANADA_COUNTRY_TERMS = {
    "canada",
    "canadian",
    "canada-open",
}

AMBIGUOUS_CITY_KEYS = {
    "hamilton",
    "london",
    "richmond",
    "surrey",
    "vancouver",
    "victoria",
    "waterloo",
}

NON_CANADIAN_COUNTRY_TERMS = {
    "australia",
    "england",
    "germany",
    "india",
    "ireland",
    "spain",
    "singapore",
    "united kingdom",
    "united states",
    "usa",
}

CONFLICTING_US_REGION_PATTERNS = {
    "richmond": {"va"},
    "vancouver": {"wa"},
}


@dataclass(frozen=True)
class CanadianLocation:
    """Structured Canadian location fields used by ingestion and filtering."""

    city: str
    province: str
    country: str
    workplace_type: str
    normalized_location: str


def normalize_search_text(value: object) -> str:
    """Return lowercase ASCII text with normalized punctuation and whitespace."""
    raw_text = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = raw_text.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower().replace("_", " ")
    return re.sub(r"\s+", " ", lowered).strip()


def has_term(text: str, term: str) -> bool:
    """Return whether a phrase appears on simple word boundaries."""
    return bool(
        re.search(
            rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
            text,
        )
    )


def infer_workplace_type(
    location_text: str,
    *,
    is_remote: bool = False,
    workplace_type: str = "",
) -> str:
    """Normalize workplace type to Remote, Hybrid, or On-site."""
    normalized_type = normalize_search_text(workplace_type)

    if is_remote or "remote" in normalized_type or "remote" in location_text:
        return "Remote"

    if "hybrid" in normalized_type or "hybrid" in location_text:
        return "Hybrid"

    return "On-site"


def find_city(location_text: str) -> tuple[str, str, str] | None:
    """Find the first known Canadian city mentioned in text."""
    matches: list[tuple[int, int, str, str, str]] = []

    for city_key, (city, province) in CITY_PROVINCES.items():
        match = re.search(
            rf"(?<![a-z0-9]){re.escape(city_key)}(?![a-z0-9])",
            location_text,
        )

        if match:
            matches.append(
                (match.start(), -len(city_key), city_key, city, province)
            )

    if matches:
        _, _, city_key, city, province = min(matches)
        return city_key, city, province

    return None


def find_provinces(location_text: str) -> list[str]:
    """Find every Canadian province or territory mentioned in text."""
    provinces: list[str] = []

    for province_name, abbreviation in PROVINCE_NAMES.items():
        if has_term(location_text, province_name) and abbreviation not in provinces:
            provinces.append(abbreviation)

    for abbreviation in PROVINCE_LABELS:
        if (
            re.search(
                rf"(?:^|[\s,;/(-]){re.escape(abbreviation.lower())}(?:$|[\s,;/)-])",
                location_text,
            )
            and abbreviation not in provinces
        ):
            provinces.append(abbreviation)

    return provinces


def has_canada_signal(text: str) -> bool:
    """Return whether text explicitly indicates Canadian eligibility."""
    return any(term in text for term in CANADA_COUNTRY_TERMS)


def has_remote_canada_eligibility(description_text: str) -> bool:
    """Detect explicit Canada eligibility language for generic remote roles."""
    eligibility_patterns = [
        r"\bbased in canada\b",
        r"\bcandidates? (?:must be )?(?:based|located) in canada\b",
        r"\bcanada[- ]only\b",
        r"\blocated (?:anywhere )?in canada\b",
        r"\breside in canada\b",
        r"\bremote (?:role|position|work) (?:in|within) canada\b",
        r"\bwork(?:ing)? from canada\b",
    ]
    return any(
        re.search(pattern, description_text)
        for pattern in eligibility_patterns
    )


def normalize_canadian_location(
    location: object,
    *,
    description: object = "",
    address_locality: object = "",
    address_region: object = "",
    address_country: object = "",
    is_remote: bool = False,
    workplace_type: str = "",
) -> CanadianLocation | None:
    """
    Normalize a Canadian job location.

    Ambiguous remote jobs are accepted only when the location, structured
    address, or description explicitly confirms Canadian eligibility.
    """
    structured_location = ", ".join(
        str(value).strip()
        for value in (address_locality, address_region, address_country)
        if str(value or "").strip()
    )
    raw_location_text = normalize_search_text(
        " ".join(part for part in (str(location or ""), structured_location) if part)
    )
    description_text = normalize_search_text(description)
    normalized_workplace_type = infer_workplace_type(
        raw_location_text,
        is_remote=is_remote,
        workplace_type=workplace_type,
    )

    city_match = find_city(raw_location_text)
    provinces = find_provinces(raw_location_text)
    province = provinces[0] if len(provinces) == 1 else ""
    country_text = normalize_search_text(address_country)
    explicit_non_canada_country = (
        country_text not in {"", "canada", "ca", "can"}
        or any(
            has_term(raw_location_text, country)
            for country in NON_CANADIAN_COUNTRY_TERMS
        )
    )
    explicit_canada = (
        has_canada_signal(raw_location_text)
        or country_text in {"canada", "ca", "can"}
        or (
            normalized_workplace_type == "Remote"
            and has_remote_canada_eligibility(description_text)
        )
    )

    if len(provinces) > 1:
        return CanadianLocation(
            city="",
            province="",
            country="Canada",
            workplace_type=normalized_workplace_type,
            normalized_location=(
                "Remote, Canada"
                if normalized_workplace_type == "Remote"
                else "Canada"
            ),
        )

    if city_match:
        city_key, city, city_province = city_match
        conflicting_regions = CONFLICTING_US_REGION_PATTERNS.get(city_key, set())
        has_conflicting_region = any(
            re.search(
                rf"(?:^|[\s,;/(-]){re.escape(region)}(?:$|[\s,;/)-])",
                raw_location_text,
            )
            for region in conflicting_regions
        )

        if explicit_non_canada_country or has_conflicting_region:
            return None

        if (
            city_key in AMBIGUOUS_CITY_KEYS
            and not explicit_canada
            and city_province not in provinces
        ):
            return None

        return CanadianLocation(
            city=city,
            province=city_province,
            country="Canada",
            workplace_type=normalized_workplace_type,
            normalized_location=f"{city}, {city_province}",
        )

    if province:
        return CanadianLocation(
            city="",
            province=province,
            country="Canada",
            workplace_type=normalized_workplace_type,
            normalized_location=f"{PROVINCE_LABELS[province]}, Canada",
        )

    if explicit_canada:
        normalized_location = (
            "Remote, Canada"
            if normalized_workplace_type == "Remote"
            or "open" in raw_location_text
            else "Canada"
        )
        return CanadianLocation(
            city="",
            province="",
            country="Canada",
            workplace_type=normalized_workplace_type,
            normalized_location=normalized_location,
        )

    return None
