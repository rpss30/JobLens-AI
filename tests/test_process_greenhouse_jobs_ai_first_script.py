import pandas as pd

from scripts.process_greenhouse_jobs_ai_first import select_sample_jobs


def test_select_sample_jobs_returns_first_rows_by_default():
    jobs_df = pd.DataFrame(
        {
            "title": [
                "Account Executive",
                "AI Engineer",
                "Backend Software Engineer",
            ]
        }
    )

    selected_df = select_sample_jobs(jobs_df, sample_size=2)

    assert selected_df["title"].tolist() == [
        "Account Executive",
        "AI Engineer",
    ]


def test_select_sample_jobs_filters_by_title_query():
    jobs_df = pd.DataFrame(
        {
            "title": [
                "Account Executive",
                "AI Engineer",
                "Senior AI Engineer",
                "Backend Software Engineer",
            ]
        }
    )

    selected_df = select_sample_jobs(
        jobs_df,
        sample_size=5,
        title_query="AI Engineer",
    )

    assert selected_df["title"].tolist() == [
        "AI Engineer",
        "Senior AI Engineer",
    ]


def test_select_sample_jobs_supports_start_row_after_filtering():
    jobs_df = pd.DataFrame(
        {
            "title": [
                "AI Engineer",
                "Senior AI Engineer",
                "Principal AI Engineer",
            ]
        }
    )

    selected_df = select_sample_jobs(
        jobs_df,
        sample_size=1,
        title_query="AI Engineer",
        start_row=1,
    )

    assert selected_df["title"].tolist() == ["Senior AI Engineer"]