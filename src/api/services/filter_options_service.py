import pandas as pd

from src.api.services.analysis_service import load_jobs_for_analysis
from src.dashboard.services import (
    get_available_locations,
    get_available_skills,
    get_available_target_roles,
    get_dataset_snapshot_summary,
)


def get_unique_column_values(jobs_df: pd.DataFrame, column: str) -> list[str]:
    """Return the sorted distinct non-empty values for one dataset column."""
    if jobs_df.empty or column not in jobs_df.columns:
        return []

    values = {
        str(value).strip()
        for value in jobs_df[column].dropna().tolist()
        if str(value).strip()
    }

    return sorted(values)


def get_filter_options(dataset_name: str | None = None) -> dict:
    """Return the selectable analysis filters and summary for one dataset."""
    resolved_dataset_name, jobs_df = load_jobs_for_analysis(dataset_name)

    return {
        "dataset_name": resolved_dataset_name,
        "target_roles": get_available_target_roles(jobs_df),
        "role_categories": get_unique_column_values(jobs_df, "role_category"),
        "skills": get_available_skills(jobs_df),
        "locations": get_available_locations(jobs_df),
        "experience_levels": get_unique_column_values(jobs_df, "experience_level"),
        "summary": get_dataset_snapshot_summary(jobs_df),
    }
