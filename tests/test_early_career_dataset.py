from pathlib import Path

from src.analysis.job_services import (
    EARLY_CAREER_GLOBAL_PATH,
    load_processed_jobs_from_csv,
)


def test_early_career_global_dataset_is_packaged_for_app() -> None:
    dataset_path = Path(EARLY_CAREER_GLOBAL_PATH)

    assert dataset_path.exists()

    jobs_df = load_processed_jobs_from_csv(str(dataset_path))

    assert len(jobs_df) == 298
    assert jobs_df["source"].eq("simplify_new_grad").all()
    assert jobs_df["experience_level"].eq("Entry Level").all()
    assert jobs_df["job_id"].is_unique
    assert jobs_df["source_url"].is_unique
    assert jobs_df["company"].nunique() >= 150
    assert jobs_df["location"].nunique() >= 100

    role_categories = set(jobs_df["role_category"].dropna().tolist())
    assert {"Software Engineering", "AI/ML", "Data Engineering"}.issubset(
        role_categories
    )

    hydration_counts = jobs_df["description_hydration_provider"].value_counts()
    assert hydration_counts["apply_page"] >= 100
    assert hydration_counts["source_index_fallback"] >= 100

    skill_coverage = (
        jobs_df["skills_text"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .mean()
    )

    assert skill_coverage >= 0.35
