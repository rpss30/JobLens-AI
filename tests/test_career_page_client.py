from src.ingestion.career_page_client import (
    extract_job_postings_from_html,
    normalize_jsonld_posting,
)


def test_extract_job_postings_from_nested_jsonld():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@graph": [
              {"@type": "Organization", "name": "Example"},
              {
                "@type": "JobPosting",
                "title": "Data Scientist",
                "description": "Build models with Python."
              }
            ]
          }
        </script>
      </head>
    </html>
    """

    postings = extract_job_postings_from_html(html)

    assert len(postings) == 1
    assert postings[0]["title"] == "Data Scientist"


def test_extract_job_postings_skips_invalid_jsonld():
    html = """
    <script type="application/ld+json">not valid json</script>
    """

    assert extract_job_postings_from_html(html) == []


def test_normalize_jsonld_posting_maps_remote_canada_fields():
    posting = {
        "@type": "JobPosting",
        "title": "Backend Engineer",
        "description": "<p>Build APIs with Python and PostgreSQL.</p>",
        "identifier": {"value": "backend-1"},
        "datePosted": "2026-06-10",
        "validThrough": "2026-07-10",
        "employmentType": "FULL_TIME",
        "jobLocationType": "TELECOMMUTE",
        "applicantLocationRequirements": {
            "@type": "Country",
            "name": "Canada",
        },
        "hiringOrganization": {"name": "Example Company"},
        "url": "https://example.com/jobs/backend-1",
    }

    normalized = normalize_jsonld_posting(
        posting,
        company_fallback="example",
        source_page_url="https://example.com/careers",
        fetched_at="2026-06-18T00:00:00+00:00",
    )

    assert normalized["job_id"] == "jsonld:example:backend-1"
    assert normalized["company"] == "Example Company"
    assert normalized["location"] == "Remote, Canada"
    assert normalized["is_remote"] is True
    assert normalized["date_posted"] == "2026-06-10"
    assert normalized["valid_through"] == "2026-07-10"
