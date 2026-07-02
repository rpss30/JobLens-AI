import pytest

from scripts.evaluate_skill_extraction import build_eval_markdown_summary, main
from src.skill_extraction.evaluation import (
    SkillExtractionCaseResult,
    SkillExtractionEvalResult,
)


def test_build_eval_markdown_summary_lists_missing_skills():
    summary = build_eval_markdown_summary(
        SkillExtractionEvalResult(
            case_count=1,
            average_recall=0.5,
            case_results=[
                SkillExtractionCaseResult(
                    id="backend",
                    expected_skills=["python", "sql"],
                    extracted_skills=["python"],
                    matched_skills=["python"],
                    missing_skills=["sql"],
                    recall=0.5,
                )
            ],
        ),
        minimum_average_recall=0.85,
    )

    assert "## Skill Extraction Evaluation" in summary
    assert "| `backend` | 50.0% | sql |" in summary


def test_main_writes_summary_when_recall_passes(tmp_path):
    summary_path = tmp_path / "skill-eval.md"

    main(summary_path=summary_path, minimum_average_recall=0.85)

    summary = summary_path.read_text(encoding="utf-8")

    assert "Average recall" in summary
    assert "backend_api_platform" in summary


def test_main_raises_when_recall_threshold_fails():
    with pytest.raises(ValueError, match="average recall"):
        main(minimum_average_recall=1.01)
