"""Run the offline skill extraction evaluation dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.processing.job_processor import extract_skills
from src.skill_extraction.evaluation import (
    DEFAULT_EVALUATION_PATH,
    SkillExtractionEvalResult,
    evaluate_skill_extractor,
    load_skill_extraction_eval_cases,
)


def build_eval_markdown_summary(
    result: SkillExtractionEvalResult,
    *,
    minimum_average_recall: float,
) -> str:
    lines = [
        "## Skill Extraction Evaluation",
        "",
        f"- Cases: **{result.case_count}**",
        f"- Average recall: **{result.average_recall:.1%}**",
        f"- Minimum required average recall: **{minimum_average_recall:.1%}**",
        "",
        "| Case | Recall | Missing skills |",
        "| --- | ---: | --- |",
    ]

    for case_result in result.case_results:
        missing_skills = (
            ", ".join(case_result.missing_skills)
            if case_result.missing_skills
            else "None"
        )
        lines.append(
            f"| `{case_result.id}` | {case_result.recall:.1%} | {missing_skills} |"
        )

    return "\n".join(lines) + "\n"


def main(
    *,
    evaluation_path: Path = DEFAULT_EVALUATION_PATH,
    minimum_average_recall: float = 0.85,
    summary_path: Path | None = None,
) -> None:
    cases = load_skill_extraction_eval_cases(evaluation_path)
    result = evaluate_skill_extractor(
        cases,
        lambda title, description: extract_skills(description),
    )
    summary = build_eval_markdown_summary(
        result,
        minimum_average_recall=minimum_average_recall,
    )

    print(summary)

    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary, encoding="utf-8")

    if result.average_recall < minimum_average_recall:
        raise ValueError(
            "Skill extraction evaluation failed: "
            f"average recall {result.average_recall:.1%} is below "
            f"{minimum_average_recall:.1%}."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate deterministic skill extraction against sample cases."
    )
    parser.add_argument(
        "--evaluation-path",
        type=Path,
        default=DEFAULT_EVALUATION_PATH,
    )
    parser.add_argument("--minimum-average-recall", type=float, default=0.85)
    parser.add_argument("--summary-path", type=Path)
    arguments = parser.parse_args()

    main(
        evaluation_path=arguments.evaluation_path,
        minimum_average_recall=arguments.minimum_average_recall,
        summary_path=arguments.summary_path,
    )
