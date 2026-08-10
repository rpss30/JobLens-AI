"""Run the offline skill extraction evaluation dataset.

This scores the deterministic dictionary extractor, which is the fallback used
when Groq is unavailable or returns nothing. The thresholds are floors measured
against the current implementation, not aspirations: the extractor is a pure
function, so any drop is a real regression rather than noise. Raise them when the
extractor improves; do not lower them to make a change pass.

Known weaknesses the dataset records rather than hides: acronym aliases such as
ML and RAG, framework names carrying version numbers, multi-word practices like
infrastructure as code, and language names appearing inside company names.
"""

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
    minimum_average_precision: float,
) -> str:
    lines = [
        "## Skill Extraction Evaluation",
        "",
        f"- Cases: **{result.case_count}**",
        f"- Average recall: **{result.average_recall:.1%}** "
        f"(minimum {minimum_average_recall:.1%})",
        f"- Average precision: **{result.average_precision:.1%}** "
        f"(minimum {minimum_average_precision:.1%})",
        f"- Average F1: **{result.average_f1:.1%}**",
        "",
        "| Case | Recall | Precision | Missing skills | Unexpected skills |",
        "| --- | ---: | ---: | --- | --- |",
    ]

    for case_result in result.case_results:
        missing_skills = (
            ", ".join(case_result.missing_skills)
            if case_result.missing_skills
            else "None"
        )
        unexpected_skills = (
            ", ".join(case_result.unexpected_skills)
            if case_result.unexpected_skills
            else "None"
        )
        lines.append(
            f"| `{case_result.id}` | {case_result.recall:.1%} | "
            f"{case_result.precision:.1%} | {missing_skills} | "
            f"{unexpected_skills} |"
        )

    return "\n".join(lines) + "\n"


# Floors, not targets. Measured at 70.4% recall and 95.0% precision over the
# 12 packaged cases; the headroom exists so that adding a deliberately hard case
# does not trip the gate, since a new case can legitimately lower the average.
# A drop past these means the extractor changed, and the numbers above should be
# re-measured and updated in the same commit.
MINIMUM_AVERAGE_RECALL = 0.65
MINIMUM_AVERAGE_PRECISION = 0.90


def main(
    *,
    evaluation_path: Path = DEFAULT_EVALUATION_PATH,
    minimum_average_recall: float = MINIMUM_AVERAGE_RECALL,
    minimum_average_precision: float = MINIMUM_AVERAGE_PRECISION,
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
        minimum_average_precision=minimum_average_precision,
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

    if result.average_precision < minimum_average_precision:
        raise ValueError(
            "Skill extraction evaluation failed: "
            f"average precision {result.average_precision:.1%} is below "
            f"{minimum_average_precision:.1%}."
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
    parser.add_argument(
        "--minimum-average-recall",
        type=float,
        default=MINIMUM_AVERAGE_RECALL,
    )
    parser.add_argument(
        "--minimum-average-precision",
        type=float,
        default=MINIMUM_AVERAGE_PRECISION,
    )
    parser.add_argument("--summary-path", type=Path)
    arguments = parser.parse_args()

    main(
        evaluation_path=arguments.evaluation_path,
        minimum_average_recall=arguments.minimum_average_recall,
        minimum_average_precision=arguments.minimum_average_precision,
        summary_path=arguments.summary_path,
    )
