import pytest

from scripts.evaluate_skill_extraction import (
    MINIMUM_AVERAGE_PRECISION,
    MINIMUM_AVERAGE_RECALL,
    build_eval_markdown_summary,
    main,
)
from src.skill_extraction.evaluation import (
    SkillExtractionCaseResult,
    SkillExtractionEvalResult,
)


def test_build_eval_markdown_summary_lists_missing_and_unexpected_skills():
    summary = build_eval_markdown_summary(
        SkillExtractionEvalResult(
            case_count=1,
            average_recall=0.5,
            average_precision=0.5,
            case_results=[
                SkillExtractionCaseResult(
                    id="backend",
                    expected_skills=["python", "sql"],
                    extracted_skills=["python", "java"],
                    matched_skills=["python"],
                    missing_skills=["sql"],
                    unexpected_skills=["java"],
                    recall=0.5,
                    precision=0.5,
                )
            ],
        ),
        minimum_average_recall=MINIMUM_AVERAGE_RECALL,
        minimum_average_precision=MINIMUM_AVERAGE_PRECISION,
    )

    assert "## Skill Extraction Evaluation" in summary
    assert "Average precision" in summary
    assert "Average F1" in summary
    # A false positive is named in the row, not just counted in the average.
    assert "| `backend` | 50.0% | 50.0% | sql | java |" in summary


def test_main_writes_summary_when_thresholds_pass(tmp_path):
    summary_path = tmp_path / "skill-eval.md"

    main(summary_path=summary_path)

    summary = summary_path.read_text(encoding="utf-8")

    assert "Average recall" in summary
    assert "Average precision" in summary
    assert "backend_api_platform" in summary


def test_main_raises_when_recall_threshold_fails():
    with pytest.raises(ValueError, match="average recall"):
        main(minimum_average_recall=1.01)


def test_main_raises_when_precision_threshold_fails():
    with pytest.raises(ValueError, match="average precision"):
        main(minimum_average_precision=1.01)
