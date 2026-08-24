from datetime import UTC, datetime

import pandas as pd

from scripts import fetch_simplify_new_grad_jobs
from src.ingestion.canada_jobs import prepare_canada_jobs
from src.ingestion.simplify_new_grad import (
    SimplifyNewGradPosting,
    normalize_simplify_new_grad_posting,
    parse_simplify_new_grad_readme,
)


LAPTOP = "\U0001f4bb"
FIRE = "\U0001f525"
GRAD = "\U0001f393"
LOCK = "\U0001f512"
SAME_COMPANY = "\u21b3"


def test_parse_simplify_new_grad_readme_reads_active_html_rows() -> None:
    readme = f"""
## {LAPTOP} Software Engineering New Grad Roles
<table>
<tr>
<td><strong><a href="https://simplify.jobs/c/ExampleCo"> {FIRE} ExampleCo</a></strong></td>
<td>Software Engineer New Grad {GRAD}</td>
<td>Toronto, ON</td>
<td><div><a href="https://example.com/apply"><img alt="Apply"></a> <a href="https://simplify.jobs/p/abc"><img alt="Simplify"></a></div></td>
<td>2d</td>
</tr>
<tr>
<td>{SAME_COMPANY}</td>
<td>Data Engineer New Grad</td>
<td><details><summary><strong>2 locations</strong></summary>Vancouver, BC</br>Seattle, WA</details></td>
<td><a href="https://example.com/data"><img alt="Apply"></a></td>
<td>0d</td>
</tr>
<tr>
<td><a href="https://simplify.jobs/c/ClosedCo">ClosedCo</a></td>
<td>Software Engineer</td>
<td>Toronto, ON</td>
<td>{LOCK}</td>
<td>3d</td>
</tr>
</table>
<details>
<summary>Inactive roles (1)</summary>
<table>
<tr>
<td><a href="https://simplify.jobs/c/InactiveCo">InactiveCo</a></td>
<td>Software Engineer New Grad</td>
<td>Toronto, ON</td>
<td><a href="https://inactive.example/apply">Apply</a></td>
<td>90d</td>
</tr>
</table>
</details>
## Data Science, AI & Machine Learning New Grad Roles
<table>
<tr>
<td><a href="https://simplify.jobs/c/DataCo">DataCo</a></td>
<td>Data Scientist New Grad</td>
<td>Remote - Canada</td>
<td><a href="https://data.example/apply">Apply</a></td>
<td>1w</td>
</tr>
</table>
"""

    postings = parse_simplify_new_grad_readme(readme)

    assert [posting.company for posting in postings] == [
        "ExampleCo",
        "ExampleCo",
        "DataCo",
    ]
    assert postings[0].category == "Software Engineering"
    assert postings[0].title == "Software Engineer New Grad"
    assert postings[0].apply_url == "https://example.com/apply"
    assert postings[0].simplify_url == "https://simplify.jobs/p/abc"
    assert postings[1].company_url == "https://simplify.jobs/c/ExampleCo"
    assert postings[1].location == "Vancouver, BC; Seattle, WA"
    assert postings[2].category == "Data Science, AI & Machine Learning"


def test_normalize_simplify_new_grad_posting_sets_entry_level_metadata() -> None:
    posting = SimplifyNewGradPosting(
        company="ExampleCo",
        title="Software Engineer New Grad",
        location="Toronto, ON",
        category="Software Engineering",
        listing_age="2d",
        apply_url="https://example.com/apply",
        company_url="https://simplify.jobs/c/ExampleCo",
        simplify_url="https://simplify.jobs/p/abc",
    )

    row = normalize_simplify_new_grad_posting(
        posting,
        fetched_at=datetime(2026, 8, 24, 12, tzinfo=UTC),
    )

    assert row["job_id"].startswith("simplify_new_grad:exampleco:")
    assert row["source"] == "simplify_new_grad"
    assert row["source_type"] == "new_grad_index"
    assert row["source_url"] == "https://example.com/apply"
    assert row["experience_level"] == "Entry Level"
    assert row["role_category"] == "Software Engineering"
    assert row["date_posted"] == "2026-08-22"
    assert row["early_career_signal"] == "new_grad"
    assert "SimplifyJobs/New-Grad-Positions" in str(row["description"])


def test_simplify_rows_can_reuse_canada_filtering() -> None:
    rows = [
        normalize_simplify_new_grad_posting(
            SimplifyNewGradPosting(
                company="CanadaCo",
                title="Software Engineer New Grad",
                location="Toronto, ON",
                category="Software Engineering",
                listing_age="0d",
                apply_url="https://canada.example/apply",
            ),
            fetched_at=datetime(2026, 8, 24, tzinfo=UTC),
        ),
        normalize_simplify_new_grad_posting(
            SimplifyNewGradPosting(
                company="UsCo",
                title="Software Engineer New Grad",
                location="Seattle, WA",
                category="Software Engineering",
                listing_age="0d",
                apply_url="https://us.example/apply",
            ),
            fetched_at=datetime(2026, 8, 24, tzinfo=UTC),
        ),
    ]

    prepared = prepare_canada_jobs(rows)

    assert len(prepared) == 1
    assert prepared[0]["company"] == "CanadaCo"
    assert prepared[0]["location"] == "Toronto, ON"
    assert prepared[0]["role_category"] == "Software Engineering"


def test_fetch_simplify_new_grad_script_writes_csv_and_summaries(
    monkeypatch,
    tmp_path,
) -> None:
    postings = [
        SimplifyNewGradPosting(
            company="ExampleCo",
            title="Software Engineer New Grad",
            location="Toronto, ON",
            category="Software Engineering",
            listing_age="0d",
            apply_url="https://example.com/apply",
        ),
        SimplifyNewGradPosting(
            company="PmCo",
            title="Associate Product Manager",
            location="Toronto, ON",
            category="Product Management",
            listing_age="0d",
            apply_url="https://pm.example/apply",
        ),
    ]

    monkeypatch.setattr(
        fetch_simplify_new_grad_jobs,
        "fetch_simplify_new_grad_postings",
        lambda readme_url: postings,
    )
    output_path = tmp_path / "simplify.csv"
    summary_path = tmp_path / "summary.json"
    markdown_path = tmp_path / "summary.md"

    fetch_simplify_new_grad_jobs.main(
        readme_url="https://example.com/readme",
        output_path=output_path,
        summary_path=summary_path,
        summary_markdown_path=markdown_path,
        canada_only=True,
    )

    output_df = pd.read_csv(output_path)

    assert output_df["company"].tolist() == ["ExampleCo"]
    assert '"source_type": "simplify_new_grad_fetch"' in summary_path.read_text(
        encoding="utf-8"
    )
    assert '"target_role_rejected_count": 1' in summary_path.read_text(
        encoding="utf-8"
    )
    assert "## Simplify New Grad Fetch Run" in markdown_path.read_text(
        encoding="utf-8"
    )
