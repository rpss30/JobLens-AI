from pathlib import Path

from src.processing.job_processor import extract_skills
from src.skill_extraction.evaluation import (
    evaluate_skill_extractor,
    load_skill_extraction_eval_cases,
)


def test_load_skill_extraction_eval_cases_from_packaged_dataset():
    cases = load_skill_extraction_eval_cases()

    assert len(cases) >= 4
    assert cases[0].id
    assert cases[0].expected_skills


def test_evaluate_skill_extractor_reports_case_recall():
    cases = load_skill_extraction_eval_cases()
    result = evaluate_skill_extractor(
        cases,
        lambda title, description: extract_skills(description),
    )

    assert result.case_count == len(cases)
    assert result.average_recall >= 0.85
    assert all(case_result.recall >= 0.75 for case_result in result.case_results)


def test_load_skill_extraction_eval_cases_rejects_non_list_payload(tmp_path):
    path = Path(tmp_path) / "bad_cases.json"
    path.write_text("{}", encoding="utf-8")

    try:
        load_skill_extraction_eval_cases(path)
    except ValueError as error:
        assert "JSON list" in str(error)
    else:
        raise AssertionError("Expected eval dataset validation to fail.")
