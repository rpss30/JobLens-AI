import pandas as pd
import inspect

from src.dashboard.app import (
    DATASET_SOURCE_CANADA,
    DEFAULT_ACTIVE_DATASET_SOURCE,
    PRESET_PROFILES,
    SEARCH_PRESETS,
    align_candidate_summary_with_match_status,
    handle_dataset_action_popover_change,
    manage_saved_datasets_dialog,
    show_delete_dataset_popover,
    show_rename_dataset_popover,
)
from src.dashboard.components import build_job_card_footer_html


def test_custom_search_and_profile_start_empty() -> None:
    assert SEARCH_PRESETS["Custom"]["target_roles"] == []
    assert PRESET_PROFILES["Custom"] == []


def test_canada_snapshot_is_the_default_dataset() -> None:
    assert DEFAULT_ACTIVE_DATASET_SOURCE == DATASET_SOURCE_CANADA


def test_dataset_actions_use_layered_popovers() -> None:
    manager_source = inspect.getsource(manage_saved_datasets_dialog)
    rename_source = inspect.getsource(show_rename_dataset_popover)
    delete_source = inspect.getsource(show_delete_dataset_popover)

    assert "show_rename_dataset_popover" in manager_source
    assert "show_delete_dataset_popover" in manager_source
    assert 'st.text_input(' not in manager_source
    assert "st.popover(" in rename_source
    assert "handle_dataset_action_popover_change" in rename_source
    assert 'st.text_input(' in rename_source
    assert "st.popover(" in delete_source
    assert '"Delete dataset"' in delete_source
    assert callable(handle_dataset_action_popover_change)


def test_search_presets_start_with_broad_experience_filter() -> None:
    assert all(
        preset["experience_level"] == "Any"
        for preset in SEARCH_PRESETS.values()
    )


def test_job_card_footer_does_not_create_blank_html_block() -> None:
    footer_html = build_job_card_footer_html(
        matched_count=6,
        missing_count=1,
    )

    assert footer_html == (
        "<span>6 matched</span><span>1 missing</span>"
    )
    assert "\n" not in footer_html


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
