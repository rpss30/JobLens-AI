"""Location normalization and demand aggregation for market insights.

Posting location is free text, and it mixes four different things: a place
("San Francisco, CA"), how the work is done ("Hybrid"), several sites in one
field ("San Francisco, CA | New York City, NY"), and a country on its own
("United States"). Counting that field as-is ranks "Hybrid" above every real
city and splits one city across its spellings, so this module pulls those
apart before anything is counted.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from src.ingestion.canada_locations import (
    PROVINCE_NAMES,
    has_term,
    normalize_search_text,
)


# One field routinely lists several sites. Comma is deliberately absent: it
# separates sites in "Dublin, London" but qualifies one place in
# "Dublin, Ireland", so it can only be read once the parts are known.
SITE_SEPARATORS = re.compile(r"[|;/]|\bor\b|\band\b", re.IGNORECASE)

# Trailing asides such as "(US/Canada)" qualify eligibility, not the site.
PARENTHETICAL = re.compile(r"\([^)]*\)")

# "Toronto ON" carries its region with no comma to announce it. Matched on
# the written case, so the English word "on" is not read as Ontario.
TRAILING_REGION = re.compile(r"^(.*?)[\s,]+([A-Z]{2})$")

# Placeholders that stand in for an empty location field.
MISSING_LOCATION_TERMS = {"na", "n a", "none", "null", "unknown", "tbd"}

# Location text that describes how the work is done rather than where it is.
# These move to the workplace-type rollup and never rank as a place.
WORKPLACE_LOCATION_TERMS = {
    "hybrid": "Hybrid",
    "remote": "Remote",
    "fully remote": "Remote",
    "distributed": "Remote",
    "work from home": "Remote",
    "in office": "On-site",
    "on site": "On-site",
    "in person": "On-site",
}

US_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "district of columbia": "DC", "florida": "FL",
    "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY",
    "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

# Regions are the one part that can be abbreviated in the source text, so both
# spellings have to resolve to the same code.
REGION_CODES = {**US_STATE_NAMES, **PROVINCE_NAMES}
REGION_ABBREVIATIONS = set(REGION_CODES.values())

# Reversed so a region standing on its own reads as a name, not a code.
REGION_LABELS = {code: name.title() for name, code in REGION_CODES.items()}

# A region settles the country, and that is what keeps London, ON apart from
# London, UK: without it the two spellings look like they qualify different
# dimensions of the same place and wrongly merge.
REGION_COUNTRIES = {
    **{code: "United States" for code in US_STATE_NAMES.values()},
    **{code: "Canada" for code in PROVINCE_NAMES.values()},
}

# A posting that never says how the work is done should not be counted as
# on-site. Saying so would invent a fact the feed does not carry.
WORKPLACE_TYPE_UNKNOWN = "Not stated"

# Only needed to recognise a country standing on its own, and to settle the
# spellings that appear as a trailing part. Anything unrecognised in trailing
# position is still treated as a country, so this list does not have to be
# exhaustive to work.
COUNTRY_LABELS = {
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "united states": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united kingdom": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "canada": "Canada",
    "ireland": "Ireland",
    "ie": "Ireland",
    "india": "India",
    "japan": "Japan",
    "singapore": "Singapore",
    "australia": "Australia",
    "france": "France",
    "germany": "Germany",
    "spain": "Spain",
    "portugal": "Portugal",
    "netherlands": "Netherlands",
    "poland": "Poland",
    "brazil": "Brazil",
    "mexico": "Mexico",
    "south korea": "South Korea",
    "korea": "South Korea",
    "china": "China",
    "new zealand": "New Zealand",
    "israel": "Israel",
    "south africa": "South Africa",
    "argentina": "Argentina",
    "colombia": "Colombia",
    "chile": "Chile",
    "italy": "Italy",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "belgium": "Belgium",
    "denmark": "Denmark",
    "norway": "Norway",
    "finland": "Finland",
    "austria": "Austria",
    "czech republic": "Czech Republic",
    "romania": "Romania",
    "ukraine": "Ukraine",
    "turkey": "Turkey",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "philippines": "Philippines",
    "indonesia": "Indonesia",
    "vietnam": "Vietnam",
    "thailand": "Thailand",
    "malaysia": "Malaysia",
    "hong kong": "Hong Kong",
    "taiwan": "Taiwan",
}

# Cities that appear under more than one name in the same feed. Kept small on
# purpose: this is for genuine aliases, not for guessing at unknown places.
CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "sfo": "San Francisco",
    "sea": "Seattle",
    "atl": "Atlanta",
    "chi": "Chicago",
    "new york city": "New York",
    "nyc": "New York",
    "sf": "San Francisco",
    "san francisco bay area": "San Francisco",
    "bay area": "San Francisco",
    "washington dc": "Washington",
    "gurgaon": "Gurugram",
    "bombay": "Mumbai",
    "calcutta": "Kolkata",
    "madras": "Chennai",
}


@dataclass(frozen=True)
class LocationParts:
    """One place mentioned by a posting, split into comparable pieces."""

    city: str
    region: str
    country: str
    # Remote is a place a job can be done from, so a posting that names no
    # city still lands somewhere the reader can pick out. Hybrid and on-site
    # are not: they say how the work happens, never where.
    remote: bool = False

    def __post_init__(self) -> None:
        if self.region and not self.country:
            object.__setattr__(
                self,
                "country",
                REGION_COUNTRIES.get(self.region, ""),
            )

    @property
    def city_key(self) -> str:
        return normalize_search_text(self.city)

    @property
    def label(self) -> str:
        """The place as it should read on screen."""
        if self.city and self.region:
            return f"{self.city}, {self.region}"

        if self.city and self.country:
            return f"{self.city}, {self.country}"

        if self.city:
            return self.city

        if self.remote:
            if self.region:
                return f"Remote, {REGION_LABELS.get(self.region, self.region)}"

            return f"Remote, {self.country}" if self.country else "Remote"

        if self.region:
            region_name = REGION_LABELS.get(self.region, self.region)
            return f"{region_name}, {self.country}" if self.country else region_name

        return self.country


@dataclass
class LocationDemandSummary:
    """Ranked places and the workplace-type rollup behind the same slice."""

    locations: list[dict] = field(default_factory=list)
    workplace_types: list[dict] = field(default_factory=list)
    # Postings whose location field held nothing but a workplace type, or
    # nothing at all. Shown so the place counts can be read honestly.
    postings_without_location: int = 0


def split_sites(location: str) -> list[str]:
    """Split a location field into the individual sites it lists."""
    fragments = SITE_SEPARATORS.split(PARENTHETICAL.sub(" ", location))
    return [fragment.strip() for fragment in fragments if fragment.strip()]


def strip_workplace_terms(part: str) -> str:
    """Remove workplace wording from a part, keeping any place it names.

    "Remote - USA" and "Remote: India" name a country as well as a way of
    working. Dropping the whole part would throw the country away with it.
    """
    remainder = normalize_search_text(part).replace("-", " ").replace(":", " ")

    # Longest first, so "fully remote" does not leave "fully" behind.
    for term in sorted(WORKPLACE_LOCATION_TERMS, key=len, reverse=True):
        remainder = re.sub(
            rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
            " ",
            remainder,
        )

    return re.sub(r"\s+", " ", remainder).strip().title()


def match_workplace_term(part: str) -> str:
    """Return the workplace type a part names, or an empty string.

    Matched on containment so that "US Remote" and "Remote in the US" are
    read the same way as a bare "Remote".
    """
    normalized = normalize_search_text(part).replace("-", " ")

    for term, workplace_type in WORKPLACE_LOCATION_TERMS.items():
        if has_term(normalized, term):
            return workplace_type

    return ""


def resolve_region(part: str, *, allow_name: bool = True) -> str:
    """Return the region code a part names, or an empty string.

    Several states share a name with a city, so "New York" and "Washington"
    are only a region where the shape of the fragment says so. An
    abbreviation is never ambiguous and always counts.
    """
    if part.strip().upper() in REGION_ABBREVIATIONS:
        return part.strip().upper()

    if allow_name and normalize_search_text(part) in REGION_CODES:
        return REGION_CODES[normalize_search_text(part)]

    return ""


def resolve_country(part: str) -> str:
    """Return the canonical country label a part names, or the part itself."""
    normalized = normalize_search_text(part)
    return COUNTRY_LABELS.get(normalized, part.strip())


def is_country(part: str) -> bool:
    """Return whether a part names a country outright."""
    return normalize_search_text(part) in COUNTRY_LABELS


def split_trailing_region(part: str) -> tuple[str, str]:
    """Split a region abbreviation that follows a city without a comma."""
    match = TRAILING_REGION.match(part.strip())

    if not match:
        return part, ""

    city, code = match.groups()

    if code not in REGION_ABBREVIATIONS or not city.strip():
        return part, ""

    return city.strip(), code


def resolve_city(part: str) -> str:
    """Return the canonical spelling of a city name."""
    normalized = normalize_search_text(part).replace(".", "")
    return CITY_ALIASES.get(normalized, part.strip())


def parse_sites(fragment: str) -> list[LocationParts]:
    """Read one comma-separated fragment into the places it names.

    Comma does two jobs at once. It qualifies a place in "San Francisco, CA"
    and it separates two of them in "Dublin, London". The parts are therefore
    read right to left: a trailing part that names a known region or country
    qualifies the city before it, and a part that names neither is a site in
    its own right. Reading an unknown trailing part as a country instead is
    what turned "San Francisco, Seattle" into a city in a country called
    Seattle.
    """
    parts = [part.strip() for part in fragment.split(",") if part.strip()]

    if not parts:
        return []

    if len(parts) == 1:
        term = match_workplace_term(parts[0])
        only = strip_workplace_terms(parts[0]) if term else parts[0]
        remote = term == "Remote"

        if not only or normalize_search_text(only) in MISSING_LOCATION_TERMS:
            return [LocationParts(city="", region="", country="", remote=True)] if remote else []

        if is_country(only):
            return [
                LocationParts(
                    city="",
                    region="",
                    country=resolve_country(only),
                    remote=remote,
                )
            ]

        city, trailing_region = split_trailing_region(only)

        return [
            LocationParts(city=resolve_city(city), region=trailing_region, country="")
        ]

    places: list[LocationParts] = []
    region = ""
    country = ""
    # Once a trailing country is set aside, a single qualified place is at
    # most "City, Region". Anything longer is a list of sites, where
    # "Seattle, San Francisco, New York" is three cities rather than a city
    # in a state, so only an abbreviation may qualify there.
    allow_region_names = len(parts) - bool(is_country(parts[-1])) <= 2

    remote = False

    for part in reversed(parts):
        term = match_workplace_term(part)

        if term:
            remote = remote or term == "Remote"
            part = strip_workplace_terms(part)

        if not part or normalize_search_text(part) in MISSING_LOCATION_TERMS:
            continue

        if is_country(part):
            if not country and not region:
                country = resolve_country(part)
            else:
                # A second country in the same fragment is its own place,
                # as in "US, Canada". It is not a city.
                places.append(
                    LocationParts(city="", region="", country=resolve_country(part))
                )

            continue

        if not region and resolve_region(part, allow_name=allow_region_names):
            region = resolve_region(part, allow_name=allow_region_names)
            continue

        city, trailing_region = split_trailing_region(part)

        places.append(
            LocationParts(
                city=resolve_city(city),
                region=region or trailing_region,
                country=country,
            )
        )
        region = ""
        country = ""

    if region or country or remote:
        # A qualification no city claimed, e.g. "Ontario, Canada", or remote
        # work scoped to one of them, e.g. "Remote, Canada".
        places.append(
            LocationParts(city="", region=region, country=country, remote=remote)
        )

    return places


# A city's region is settled by weight of evidence. Reading a city list as
# a qualified place leaves a few stray pairings behind, and they should not
# outvote the spelling the feed uses hundreds of times.
DOMINANT_QUALIFICATION_SHARE = 0.8


def dominant_value(totals: dict[str, int]) -> str:
    """Return the value carrying the qualifications, or "" if they disagree."""
    if not totals:
        return ""

    value, count = max(totals.items(), key=lambda item: item[1])

    return value if count >= sum(totals.values()) * DOMINANT_QUALIFICATION_SHARE else ""


def canonical_spellings(
    counts: dict[LocationParts, int],
) -> dict[LocationParts, LocationParts]:
    """Map each spelling of a city to the single place they all mean.

    "Dublin" and "Dublin, Ireland" are one place, and so are
    "New York, New York, USA" and "New York City, NY". A city folds into the
    region and country that carry its qualified mentions; where those are
    contested, as London, ON and London, UK would be, the spellings stay
    apart rather than guess at what a bare mention meant.
    """
    grouped: dict[str, list[LocationParts]] = defaultdict(list)

    for parts in counts:
        if parts.city:
            grouped[parts.city_key].append(parts)

    canonical: dict[LocationParts, LocationParts] = {}

    for spellings in grouped.values():
        region_totals: dict[str, int] = defaultdict(int)
        country_totals: dict[str, int] = defaultdict(int)

        for parts in spellings:
            if parts.region:
                region_totals[parts.region] += counts[parts]

            if parts.country:
                country_totals[parts.country] += counts[parts]

        region = dominant_value(region_totals)
        country = dominant_value(country_totals)

        # Genuinely contested, as London, ON and London, UK would be. There
        # is no way to tell which one a bare "London" meant, so nothing moves.
        if (region_totals and not region) or (country_totals and not country):
            continue

        merged = LocationParts(
            city=spellings[0].city,
            region=region,
            country=country,
        )

        for parts in spellings:
            canonical[parts] = merged

    return canonical


def merge_location_spellings(
    counts: dict[LocationParts, int],
) -> dict[LocationParts, int]:
    """Total each place once its spellings have been folded together."""
    canonical = canonical_spellings(counts)
    totals: dict[LocationParts, int] = defaultdict(int)

    for parts, count in counts.items():
        totals[canonical.get(parts, parts)] += count

    return dict(totals)


def places_by_row(jobs_df: pd.DataFrame) -> list[list[LocationParts]]:
    """Return the places each posting names, in row order."""
    if jobs_df.empty or "location" not in jobs_df.columns:
        return []

    rows: list[list[LocationParts]] = []

    for _, row in jobs_df.iterrows():
        location = str(row.get("location") or "").strip()
        places = [
            parts
            for fragment in split_sites(location)
            for parts in parse_sites(fragment)
            if parts.label
        ]
        # One posting should not count twice for a city it lists twice.
        rows.append(list(dict.fromkeys(places)))

    return rows


def place_labels_by_row(jobs_df: pd.DataFrame) -> list[set[str]]:
    """Return the place labels each posting is counted under, in row order.

    The same parsing and folding the ranked list uses, so a filter built on
    these labels selects exactly the postings a count promised. Matching on
    words instead lets "Canada" pull in "Remote, Canada" and "Ontario,
    Canada", and "Toronto, ON" pull in every location holding "on".
    """
    rows = places_by_row(jobs_df)
    counts: dict[LocationParts, int] = defaultdict(int)

    for places in rows:
        for parts in places:
            counts[parts] += 1

    canonical = canonical_spellings(counts)

    return [{canonical.get(parts, parts).label for parts in places} for places in rows]


def resolve_workplace_type(
    location: str,
    *,
    declared_type: str = "",
    is_remote: bool = False,
) -> str:
    """Return how the work is done, or that the posting never says."""
    declared = normalize_search_text(declared_type).replace("-", " ")

    if declared:
        return WORKPLACE_LOCATION_TERMS.get(declared, declared_type.strip())

    if is_remote:
        return "Remote"

    normalized_location = normalize_search_text(location).replace("-", " ")

    for term, workplace_type in WORKPLACE_LOCATION_TERMS.items():
        if has_term(normalized_location, term):
            return workplace_type

    return WORKPLACE_TYPE_UNKNOWN


def summarize_location_demand(
    jobs_df: pd.DataFrame,
    top_n: int | None = None,
) -> LocationDemandSummary:
    """Return ranked places and workplace types for a slice of postings.

    A posting open in several cities counts once for each of them, so the
    place counts add up to more than the number of postings. That mirrors how
    skill demand already counts a posting once per skill it asks for.
    """
    summary = LocationDemandSummary()

    if jobs_df.empty or "location" not in jobs_df.columns:
        return summary

    place_counts: dict[LocationParts, int] = defaultdict(int)
    workplace_counts: dict[str, int] = defaultdict(int)
    has_workplace_column = "workplace_type" in jobs_df.columns
    has_remote_column = "is_remote" in jobs_df.columns

    for (_, row), places in zip(jobs_df.iterrows(), places_by_row(jobs_df)):
        location = str(row.get("location") or "").strip()

        # The Canada snapshot carries these outright; the Greenhouse feeds
        # only imply them through the location text, and often not at all.
        workplace_type = resolve_workplace_type(
            location,
            declared_type=(
                str(row.get("workplace_type") or "") if has_workplace_column else ""
            ),
            is_remote=bool(row.get("is_remote")) if has_remote_column else False,
        )
        workplace_counts[workplace_type] += 1

        if not places:
            summary.postings_without_location += 1
            continue

        for parts in places:
            place_counts[parts] += 1

    merged = merge_location_spellings(place_counts)

    ranked = sorted(merged.items(), key=lambda item: (-item[1], item[0].label))

    if top_n is not None:
        ranked = ranked[:top_n]

    summary.locations = [
        {
            "location": parts.label,
            "city": parts.city,
            "region": parts.region,
            "country": parts.country,
            "remote": parts.remote,
            "job_count": count,
        }
        for parts, count in ranked
    ]

    summary.workplace_types = [
        {"workplace_type": workplace_type, "job_count": count}
        for workplace_type, count in sorted(
            workplace_counts.items(),
            key=lambda item: -item[1],
        )
    ]

    return summary
