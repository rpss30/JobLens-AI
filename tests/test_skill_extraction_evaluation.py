from pathlib import Path

from scripts.evaluate_skill_extraction import (
    MINIMUM_AVERAGE_PRECISION,
    MINIMUM_AVERAGE_RECALL,
)
from src.processing.job_processor import extract_skills
from src.skill_extraction.evaluation import (
    evaluate_skill_extractor,
    load_skill_extraction_eval_cases,
)


def deterministic_extractor(title: str, description: str) -> list[str]:
    return extract_skills(description)


def test_load_skill_extraction_eval_cases_from_packaged_dataset():
    cases = load_skill_extraction_eval_cases()

    assert len(cases) >= 12
    assert cases[0].id
    assert cases[0].expected_skills

    # Case ids are referenced in the evaluation summary, so they must be unique.
    assert len({case.id for case in cases}) == len(cases)


def test_evaluate_skill_extractor_reports_recall_and_precision():
    cases = load_skill_extraction_eval_cases()
    result = evaluate_skill_extractor(cases, deterministic_extractor)

    assert result.case_count == len(cases)
    assert result.average_recall >= MINIMUM_AVERAGE_RECALL
    assert result.average_precision >= MINIMUM_AVERAGE_PRECISION

    for case_result in result.case_results:
        # Every expected skill is either matched or missing, and everything the
        # extractor returned is either matched or unexpected.
        assert len(case_result.matched_skills) + len(
            case_result.missing_skills
        ) == len(case_result.expected_skills)
        assert len(case_result.matched_skills) + len(
            case_result.unexpected_skills
        ) == len(case_result.extracted_skills)
        assert 0.0 <= case_result.recall <= 1.0
        assert 0.0 <= case_result.precision <= 1.0
        assert 0.0 <= case_result.f1 <= 1.0


def test_precision_penalises_an_extractor_that_returns_everything():
    """This is why precision was added.

    Recall alone cannot tell a careful extractor from one that dumps its whole
    vocabulary at every posting, and the second scores perfectly on recall.
    """
    cases = load_skill_extraction_eval_cases()
    whole_vocabulary = [
        "python",
        "sql",
        "aws",
        "docker",
        "kubernetes",
        "terraform",
        "spark",
        "airflow",
        "pytorch",
        "tensorflow",
        "react",
        "typescript",
        "redis",
        "mongodb",
        "tableau",
        "excel",
    ]

    result = evaluate_skill_extractor(cases, lambda title, text: whole_vocabulary)

    assert result.average_recall > 0.0
    assert result.average_precision < 0.5
    assert result.average_f1 < result.average_recall


def test_baseline_list_cases_are_fully_extracted():
    """The plain-list cases are the floor the dictionary extractor must hold.

    The harder cases exist to record known weaknesses; these do not get to
    regress quietly behind an average.
    """
    results = {
        case_result.id: case_result
        for case_result in evaluate_skill_extractor(
            load_skill_extraction_eval_cases(),
            deterministic_extractor,
        ).case_results
    }

    for case_id in [
        "backend_api_platform",
        "cloud_data_platform",
        "analytics_bi",
        "prose_without_a_skill_list",
        "soft_skills_are_not_technical_skills",
    ]:
        assert results[case_id].recall == 1.0, case_id


def test_load_skill_extraction_eval_cases_rejects_non_list_payload(tmp_path):
    path = Path(tmp_path) / "bad_cases.json"
    path.write_text("{}", encoding="utf-8")

    try:
        load_skill_extraction_eval_cases(path)
    except ValueError as error:
        assert "JSON list" in str(error)
    else:
        raise AssertionError("Expected eval dataset validation to fail.")
