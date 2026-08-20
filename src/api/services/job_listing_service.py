from typing import Literal

import pandas as pd

from src.api.errors import ApiError
from src.api.schemas import JobListResponse
from src.api.services.analysis_service import clean_optional_text, load_jobs_for_analysis
from src.api.services.listing import paginate_items, sort_items
from src.analysis.companies import company_domain
from src.analysis.job_services import filter_jobs
from src.database import repository as database_repository


JobSortBy = Literal[
    "search_relevance",
    "title",
    "company",
    "location",
    "date_posted",
]


def clean_optional_flag(value: object) -> bool:
    """Return a boolean for optional posting flags stored as text or numbers."""
    if isinstance(value, bool):
        return value

    return clean_optional_text(value).lower() in {"true", "yes", "1"}


def build_job_listing_row(row: pd.Series) -> dict:
    """Map one processed job posting to its browse-friendly listing fields."""
    skills = row.get("extracted_skills", [])

    if not isinstance(skills, list):
        skills = []

    return {
        "job_id": clean_optional_text(row.get("job_id", "")),
        "title": clean_optional_text(row.get("title", "")),
        "company": clean_optional_text(row.get("company", "")),
        "company_domain": company_domain(
            clean_optional_text(row.get("company", "")),
            [row.get("source_url", "")],
        ),
        "location": clean_optional_text(row.get("location", "")),
        "experience_level": clean_optional_text(row.get("experience_level", "")),
        "role_category": clean_optional_text(row.get("role_category", "")),
        "employment_type": clean_optional_text(row.get("employment_type", "")),
        "workplace_type": clean_optional_text(row.get("workplace_type", "")),
        "is_remote": clean_optional_flag(row.get("is_remote", False)),
        "date_posted": clean_optional_text(row.get("date_posted", "")),
        "source": clean_optional_text(row.get("source", "")),
        "source_url": clean_optional_text(row.get("source_url", "")),
        "skills": [str(skill).strip() for skill in skills if str(skill).strip()],
        "search_relevance": float(row.get("search_relevance", 0.0) or 0.0),
    }


# Copied onto a stand-in row when the posting behind a save has left the
# dataset. Names match the dataset's own columns so the row needs no special
# handling once it is in the frame.
SAVED_SNAPSHOT_FIELDS = (
    "title",
    "company",
    "location",
    "source_url",
    "date_posted",
    "experience_level",
)


def saved_postings_frame(
    *,
    dataset_name: str,
    jobs_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return the saved postings for a dataset as listing rows.

    A save is a snapshot taken when the bookmark was clicked, so it outlives
    the posting it came from. Where that posting is still in the dataset the
    dataset row wins, being the fresher of the two; where it has gone the
    snapshot stands in, which is the whole reason the details are copied.

    Rows come back in the order they were saved, newest first, so a listing
    that has nothing to rank by still reads sensibly.
    """
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so saved jobs cannot be listed.",
        )

    saved = database_repository.list_saved_jobs(dataset_name=dataset_name)

    if not saved:
        return jobs_df.iloc[0:0]

    saved_ids = {str(entry["job_id"]) for entry in saved}
    has_rows = not jobs_df.empty and "job_id" in jobs_df.columns

    present = (
        jobs_df[jobs_df["job_id"].astype(str).isin(saved_ids)]
        if has_rows
        else jobs_df.iloc[0:0]
    )
    present_ids = (
        set(present["job_id"].astype(str)) if not present.empty else set()
    )

    stand_ins = [
        {
            "job_id": str(entry["job_id"]),
            **{field: entry.get(field, "") or "" for field in SAVED_SNAPSHOT_FIELDS},
        }
        for entry in saved
        if str(entry["job_id"]) not in present_ids
    ]

    if stand_ins:
        stand_in_frame = pd.DataFrame(stand_ins)

        # Matched to the dataset's shape so the two halves concatenate into
        # one frame the filters can read without special cases.
        if len(jobs_df.columns):
            stand_in_frame = stand_in_frame.reindex(
                columns=jobs_df.columns,
                fill_value="",
            )

        frame = pd.concat([present, stand_in_frame], ignore_index=True)
    else:
        frame = present.reset_index(drop=True)

    saved_order = {str(entry["job_id"]): index for index, entry in enumerate(saved)}

    return (
        frame.assign(
            _saved_rank=frame["job_id"].astype(str).map(saved_order),
        )
        .sort_values("_saved_rank", kind="stable")
        .drop(columns="_saved_rank")
        .reset_index(drop=True)
    )


def list_jobs(
    *,
    dataset_name: str | None = None,
    target_roles: list[str] | None = None,
    search_query: str = "",
    search_mode: str = "tfidf",
    location: str = "Any",
    experience_level: str = "Any",
    company: str = "Any",
    sort_by: JobSortBy = "search_relevance",
    sort_order: str = "desc",
    limit: int = 20,
    offset: int = 0,
    saved_only: bool = False,
) -> JobListResponse:
    """Return a filtered, sorted, and paginated slice of job postings."""
    resolved_dataset_name, jobs_df = load_jobs_for_analysis(dataset_name)

    if saved_only:
        # Narrowed before the filters run, so searching and sorting apply to
        # the saved set exactly as they do to the dataset.
        jobs_df = saved_postings_frame(
            dataset_name=resolved_dataset_name,
            jobs_df=jobs_df,
        )

    filtered_jobs = filter_jobs(
        df=jobs_df,
        target_roles=target_roles or [],
        location=location,
        experience_level=experience_level,
        search_query=search_query,
        search_mode=search_mode,
        company=company,
    )

    jobs = [build_job_listing_row(row) for _, row in filtered_jobs.iterrows()]
    jobs = sort_items(jobs, sort_by=sort_by, sort_order=sort_order)

    return JobListResponse(
        dataset_name=resolved_dataset_name,
        total=len(jobs),
        limit=limit,
        offset=offset,
        jobs=paginate_items(jobs, limit=limit, offset=offset),
    )


def get_job(*, dataset_name: str | None, job_id: str) -> dict:
    """Return one posting, including the description the list leaves out.

    Descriptions run to several kilobytes each, so they travel one at a time
    rather than riding along with every row of a list nobody has opened yet.
    """
    resolved_dataset_name, jobs_df = load_jobs_for_analysis(dataset_name)

    if jobs_df.empty or "job_id" not in jobs_df.columns:
        raise ApiError(status_code=404, detail="That job posting was not found.")

    matches = jobs_df[jobs_df["job_id"].astype(str) == str(job_id)]

    if matches.empty:
        raise ApiError(status_code=404, detail="That job posting was not found.")

    row = matches.iloc[0]

    return {
        **build_job_listing_row(row),
        "dataset_name": resolved_dataset_name,
        "description": clean_optional_text(row.get("description", "")),
        # Not cleaned: the line breaks are the whole point of this field.
        "description_formatted": str(row.get("description_formatted") or "").strip(),
    }
