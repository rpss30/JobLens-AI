import pandas as pd

from scripts.build_greenhouse_ai_demo_jobs import select_jobs_for_queries


def test_select_jobs_for_queries_selects_matching_titles_per_query():
    jobs_df = pd.DataFrame(
        [
            {"job_id": "1", "title": "AI Engineer"},
            {"job_id": "2", "title": "Senior AI Engineer"},
            {"job_id": "3", "title": "Backend Software Engineer"},
            {"job_id": "4", "title": "Data Scientist"},
            {"job_id": "5", "title": "Account Executive"},
        ]
    )

    selected_df = select_jobs_for_queries(
        jobs_df=jobs_df,
        title_queries=["AI Engineer", "Backend Software Engineer"],
        jobs_per_query=1,
    )

    assert selected_df["title"].tolist() == [
        "AI Engineer",
        "Backend Software Engineer",
    ]


def test_select_jobs_for_queries_deduplicates_jobs_across_queries():
    jobs_df = pd.DataFrame(
        [
            {"job_id": "1", "title": "Senior AI Engineer"},
            {"job_id": "2", "title": "Platform Engineer"},
        ]
    )

    selected_df = select_jobs_for_queries(
        jobs_df=jobs_df,
        title_queries=["AI Engineer", "Senior AI Engineer"],
        jobs_per_query=2,
    )

    assert selected_df["job_id"].tolist() == ["1"]


def test_select_jobs_for_queries_returns_empty_dataframe_when_no_matches():
    jobs_df = pd.DataFrame(
        [
            {"job_id": "1", "title": "Account Executive"},
            {"job_id": "2", "title": "Legal Counsel"},
        ]
    )

    selected_df = select_jobs_for_queries(
        jobs_df=jobs_df,
        title_queries=["AI Engineer"],
        jobs_per_query=2,
    )

    assert selected_df.empty