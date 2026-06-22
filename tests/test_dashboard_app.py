import pandas as pd

from src.dashboard.app import (
    SEARCH_PRESETS,
    align_candidate_summary_with_match_status,
)


def test_search_presets_start_with_broad_experience_filter() -> None:
    assert all(
        preset["experience_level"] == "Any"
        for preset in SEARCH_PRESETS.values()
    )


def test_align_candidate_summary_replaces_stale_zero_match_copy() -> None:
    candidate_summary = {
        "summary": (
            "Based on <strong>2 matching postings</strong>, your strongest fit is "
            "<span class='summary-highlight'>Software Engineering</span> with a "
            "<strong>0.0% weighted match</strong>."
        ),
        "matched_skills": [],
        "missing_skills": ["go", "java", "sql"],
    }
    role_scores_df = pd.DataFrame(
        [
            {
                "role_category": "Software Engineering",
                "weighted_match_score": 0.0,
                "total_possible_weight": 12,
            }
        ]
    )

    aligned_summary = align_candidate_summary_with_match_status(
        candidate_summary=candidate_summary,
        role_scores_df=role_scores_df,
        best_score=0.0,
        top_missing_skill="go",
        jobs_analyzed=2,
    )

    assert "no overlap" in aligned_summary["summary"]
    assert "strongest fit" not in aligned_summary["summary"]
    assert "0.0% weighted match" not in aligned_summary["summary"]
    assert aligned_summary["matched_skills"] == []
    assert aligned_summary["missing_skills"] == ["go", "java", "sql"]
