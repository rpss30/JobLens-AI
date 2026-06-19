from src.ingestion.canada_locations import normalize_canadian_location


def test_normalize_canadian_location_standardizes_city_and_province():
    location = normalize_canadian_location("Toronto, Ontario, Canada")

    assert location is not None
    assert location.city == "Toronto"
    assert location.province == "ON"
    assert location.normalized_location == "Toronto, ON"
    assert location.workplace_type == "On-site"


def test_normalize_canadian_location_handles_accents_and_province_names():
    location = normalize_canadian_location("Montréal, Québec")

    assert location is not None
    assert location.normalized_location == "Montreal, QC"


def test_normalize_canadian_location_handles_remote_canada():
    location = normalize_canadian_location("Remote in Canada")

    assert location is not None
    assert location.normalized_location == "Remote, Canada"
    assert location.workplace_type == "Remote"


def test_normalize_canadian_location_uses_structured_address():
    location = normalize_canadian_location(
        "",
        address_locality="Vancouver",
        address_region="British Columbia",
        address_country="Canada",
        workplace_type="Hybrid",
    )

    assert location is not None
    assert location.normalized_location == "Vancouver, BC"
    assert location.workplace_type == "Hybrid"


def test_normalize_canadian_location_accepts_remote_description_eligibility():
    location = normalize_canadian_location(
        "Remote",
        description="Candidates must be located in Canada.",
        is_remote=True,
    )

    assert location is not None
    assert location.normalized_location == "Remote, Canada"


def test_normalize_canadian_location_rejects_non_canadian_job():
    assert normalize_canadian_location("Seattle, WA") is None
    assert normalize_canadian_location("Remote - USA") is None
    assert normalize_canadian_location("London, UK") is None
    assert normalize_canadian_location("Vancouver, WA") is None


def test_normalize_canadian_location_requires_context_for_ambiguous_city():
    assert normalize_canadian_location("London") is None

    location = normalize_canadian_location("London, ON")

    assert location is not None
    assert location.normalized_location == "London, ON"
