import pandas as pd

from src.dashboard.services import (
    load_processed_jobs_from_csv,
    parse_extracted_skills_value,
    prepare_processed_jobs_for_dashboard,
)


def test_parse_extracted_skills_value_handles_python_list_string():
    value = "['Python', 'SQL', 'AWS']"

    assert parse_extracted_skills_value(value) == ["Python", "SQL", "AWS"]


def test_parse_extracted_skills_value_handles_comma_separated_string():
    value = "Python, SQL, AWS"

    assert parse_extracted_skills_value(value) == ["Python", "SQL", "AWS"]


def test_parse_extracted_skills_value_handles_empty_values():
    assert parse_extracted_skills_value("") == []
    assert parse_extracted_skills_value(None) == []


def test_prepare_processed_jobs_for_dashboard_parses_skills_and_adds_skills_text():
    df = pd.DataFrame(
        {
            "title": ["AI Engineer"],
            "extracted_skills": ["['Python', 'SQL']"],
        }
    )

    prepared_df = prepare_processed_jobs_for_dashboard(df)

    assert prepared_df.loc[0, "extracted_skills"] == ["Python", "SQL"]
    assert prepared_df.loc[0, "skills_text"] == "Python, SQL"


def test_load_processed_jobs_from_csv_returns_empty_dataframe_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.csv"

    loaded_df = load_processed_jobs_from_csv(str(missing_path))

    assert loaded_df.empty


def test_load_processed_jobs_from_csv_loads_and_prepares_existing_file(tmp_path):
    csv_path = tmp_path / "processed_jobs.csv"

    df = pd.DataFrame(
        {
            "title": ["AI Engineer"],
            "extracted_skills": ["['Python', 'SQL']"],
        }
    )
    df.to_csv(csv_path, index=False)

    loaded_df = load_processed_jobs_from_csv(str(csv_path))

    assert loaded_df.loc[0, "extracted_skills"] == ["Python", "SQL"]
    assert loaded_df.loc[0, "skills_text"] == "Python, SQL"