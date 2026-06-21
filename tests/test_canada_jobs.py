from datetime import UTC, datetime

from src.ingestion.canada_jobs import (
    deduplicate_jobs,
    is_posting_active,
    is_target_technical_job,
    prepare_canada_jobs,
    select_balanced_jobs,
)


def test_is_target_technical_job_accepts_target_roles():
    assert is_target_technical_job({"title": "Senior Data Engineer"}) is True
    assert is_target_technical_job({"title": "Backend Software Engineer"}) is True


def test_is_target_technical_job_rejects_non_target_and_management_roles():
    assert is_target_technical_job({"title": "Account Executive"}) is False
    assert is_target_technical_job({"title": "Engineering Manager, Data"}) is False
    assert is_target_technical_job(
        {"title": "Future Opportunities: Software Engineer"}
    ) is False
    assert is_target_technical_job({"title": "VP, AI Platform Engineering"}) is False
    assert is_target_technical_job(
        {"title": "Data Annotation Specialist, Software Engineering"}
    ) is False


def test_is_posting_active_uses_explicit_valid_through_date():
    as_of = datetime(2026, 6, 18, tzinfo=UTC)

    assert is_posting_active({"valid_through": "2026-06-20"}, as_of=as_of) is True
    assert is_posting_active({"valid_through": "2026-06-10"}, as_of=as_of) is False
    assert is_posting_active({"valid_through": ""}, as_of=as_of) is True


def test_prepare_canada_jobs_filters_and_normalizes_postings():
    jobs = [
        {
            "job_id": "1",
            "title": "Data Engineer",
            "company": "Example",
            "location": "Toronto, Ontario, Canada",
            "description": "Build data pipelines with Python and SQL.",
        },
        {
            "job_id": "2",
            "title": "Data Engineer",
            "company": "Example",
            "location": "Seattle, WA",
            "description": "Build data pipelines.",
        },
        {
            "job_id": "3",
            "title": "Account Executive",
            "company": "Example",
            "location": "Toronto, Canada",
            "description": "Sell software.",
        },
    ]

    prepared = prepare_canada_jobs(jobs)

    assert len(prepared) == 1
    assert prepared[0]["location"] == "Toronto, ON"
    assert prepared[0]["province"] == "ON"
    assert prepared[0]["role_category"] == "Data Engineering"


def test_deduplicate_jobs_prefers_stable_job_id():
    jobs = [
        {"job_id": "greenhouse:example:1", "title": "Data Engineer"},
        {"job_id": "greenhouse:example:1", "title": "Updated title"},
    ]

    assert deduplicate_jobs(jobs) == [jobs[0]]


def test_deduplicate_jobs_removes_visible_duplicate_with_different_ids():
    jobs = [
        {
            "job_id": "ashby:example:1",
            "source_url": "https://example.com/jobs/1",
            "company": "Example",
            "title": "Software Engineer",
            "location": "Remote, Canada",
        },
        {
            "job_id": "ashby:example:2",
            "source_url": "https://example.com/jobs/2",
            "company": "Example",
            "title": "Software Engineer",
            "location": "Remote, Canada",
        },
    ]

    assert deduplicate_jobs(jobs) == [jobs[0]]


def test_select_balanced_jobs_limits_company_and_includes_role_categories():
    jobs = [
        {
            "job_id": str(index),
            "company": company,
            "location": location,
            "title": title,
            "role_category": category,
            "date_posted": f"2026-06-{10 + index:02d}",
        }
        for index, (company, location, title, category) in enumerate(
            [
                ("A", "Toronto, ON", "Data Engineer", "Data Engineering"),
                ("A", "Toronto, ON", "Data Engineer II", "Data Engineering"),
                ("B", "Vancouver, BC", "Software Engineer", "Software Engineering"),
                ("C", "Montreal, QC", "Data Scientist", "Data Science"),
            ]
        )
    ]

    selected = select_balanced_jobs(
        jobs,
        max_jobs=4,
        max_per_company=1,
        max_per_location=2,
    )

    assert len(selected) == 3
    assert {job["role_category"] for job in selected} == {
        "Data Engineering",
        "Data Science",
        "Software Engineering",
    }
