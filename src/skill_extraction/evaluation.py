"""Offline evaluation helpers for skill extraction quality checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from src.skill_extraction.normalizer import normalize_skill_list


DEFAULT_EVALUATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation"
    / "skill_extraction_cases.json"
)


@dataclass(frozen=True)
class SkillExtractionEvalCase:
    id: str
    title: str
    description: str
    expected_skills: list[str]


@dataclass(frozen=True)
class SkillExtractionCaseResult:
    id: str
    expected_skills: list[str]
    extracted_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    unexpected_skills: list[str]
    recall: float
    precision: float

    @property
    def f1(self) -> float:
        if not self.recall or not self.precision:
            return 0.0

        return (
            2 * self.recall * self.precision / (self.recall + self.precision)
        )


@dataclass(frozen=True)
class SkillExtractionEvalResult:
    case_count: int
    average_recall: float
    average_precision: float
    case_results: list[SkillExtractionCaseResult]

    @property
    def average_f1(self) -> float:
        if not self.case_results:
            return 0.0

        return sum(result.f1 for result in self.case_results) / len(
            self.case_results
        )


def load_skill_extraction_eval_cases(
    path: Path = DEFAULT_EVALUATION_PATH,
) -> list[SkillExtractionEvalCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, list):
        raise ValueError("Skill extraction eval dataset must be a JSON list.")

    cases: list[SkillExtractionEvalCase] = []

    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Every skill extraction eval case must be an object.")

        cases.append(
            SkillExtractionEvalCase(
                id=str(item["id"]),
                title=str(item["title"]),
                description=str(item["description"]),
                expected_skills=normalize_skill_list(
                    list(item["expected_skills"]),
                    max_skills=50,
                ),
            )
        )

    return cases


def evaluate_skill_extractor(
    cases: Iterable[SkillExtractionEvalCase],
    extractor: Callable[[str, str], list[str]],
) -> SkillExtractionEvalResult:
    case_results: list[SkillExtractionCaseResult] = []

    for case in cases:
        extracted_skills = normalize_skill_list(
            extractor(case.title, case.description),
            max_skills=50,
        )
        expected_set = set(case.expected_skills)
        extracted_set = set(extracted_skills)
        matched_skills = sorted(expected_set & extracted_set)
        missing_skills = sorted(expected_set - extracted_set)
        unexpected_skills = sorted(extracted_set - expected_set)
        recall = (
            len(matched_skills) / len(case.expected_skills)
            if case.expected_skills
            else 1.0
        )
        # Recall alone rewards an extractor that returns its whole vocabulary,
        # so every case is scored for what it invented as well as what it found.
        precision = (
            len(matched_skills) / len(extracted_skills)
            if extracted_skills
            else 1.0
        )

        case_results.append(
            SkillExtractionCaseResult(
                id=case.id,
                expected_skills=case.expected_skills,
                extracted_skills=extracted_skills,
                matched_skills=matched_skills,
                missing_skills=missing_skills,
                unexpected_skills=unexpected_skills,
                recall=recall,
                precision=precision,
            )
        )

    average_recall = (
        sum(result.recall for result in case_results) / len(case_results)
        if case_results
        else 0.0
    )
    average_precision = (
        sum(result.precision for result in case_results) / len(case_results)
        if case_results
        else 0.0
    )

    return SkillExtractionEvalResult(
        case_count=len(case_results),
        average_recall=average_recall,
        average_precision=average_precision,
        case_results=case_results,
    )
