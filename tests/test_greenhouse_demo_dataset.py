from pathlib import Path

from src.dashboard.services import (
    GREENHOUSE_AI_DEMO_PATH,
    load_processed_jobs_from_csv,
)


def test_greenhouse_ai_demo_dataset_is_packaged_for_dashboard() -> None:
    demo_dataset_path = Path(GREENHOUSE_AI_DEMO_PATH)

    assert demo_dataset_path.exists()

    demo_jobs_df = load_processed_jobs_from_csv(str(demo_dataset_path))

    assert not demo_jobs_df.empty

    required_columns = {
        "title",
        "company",
        "location",
        "experience_level",
        "role_category",
        "extracted_skills",
        "skills_text",
    }

    assert required_columns.issubset(set(demo_jobs_df.columns))

    role_categories = set(demo_jobs_df["role_category"].dropna().tolist())

    assert {"AI/ML", "Software Engineering", "Data Science"}.issubset(
        role_categories
    )
