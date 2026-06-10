import pandas as pd

from scripts.process_greenhouse_jobs_ai_first import main, select_sample_jobs


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

def test_main_accepts_custom_output_path(tmp_path, monkeypatch):
    input_path = tmp_path / "greenhouse_jobs.csv"
    output_path = tmp_path / "custom_output.csv"

    jobs_df = pd.DataFrame(
        [
            {
                "job_id": "greenhouse:test:1",
                "title": "AI Engineer",
                "company": "test",
                "location": "Remote",
                "description": "Build AI systems with Python.",
                "experience_level": "Mid Level",
                "source": "greenhouse",
                "source_url": "https://example.com/job/1",
                "fetched_at": "2026-06-10T00:00:00+00:00",
                "is_target_job": True,
            }
        ]
    )
    jobs_df.to_csv(input_path, index=False)

    class FakeExtractionResult:
        skills = ["python"]
        provider = "groq"
        error = ""

    monkeypatch.setattr(
        "scripts.process_greenhouse_jobs_ai_first.INPUT_PATH",
        input_path,
    )
    monkeypatch.setattr(
        "scripts.process_greenhouse_jobs_ai_first.extract_skills_ai_first",
        lambda **kwargs: FakeExtractionResult(),
    )
    monkeypatch.setattr(
        "scripts.process_greenhouse_jobs_ai_first.time.sleep",
        lambda seconds: None,
    )

    main(sample_size=1, delay_seconds=0, output_path=output_path)

    assert output_path.exists()

    output_df = pd.read_csv(output_path)

    assert output_df.loc[0, "title"] == "AI Engineer"
    assert output_df.loc[0, "skill_extraction_provider"] == "groq"
    assert output_df.loc[0, "skills_text"] == "python"