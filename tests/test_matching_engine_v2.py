import pandas as pd

from src.dashboard.services import filter_jobs, load_processed_jobs_from_csv
from src.matching.match_engine import (
    build_skill_match_map,
    get_skill_similarity,
    score_roles,
    select_best_role_row,
)


CANADA_SNAPSHOT_PATH = "data/processed/canada_jobs_snapshot.csv"
SOFTWARE_TARGET_ROLES = [
    "Backend Developer",
    "Backend Engineer",
    "Software Engineer",
    "Full Stack Developer",
]


def make_job(
    title: str,
    role_category: str,
    skills: list[str],
) -> dict:
    return {
        "title": title,
        "company": "TestCo",
        "location": "Remote, Canada",
        "experience_level": "Any",
        "role_category": role_category,
        "extracted_skills": skills,
        "skills_text": ", ".join(skills),
    }


def test_skill_similarity_recognizes_variants_without_conflating_languages() -> None:
    assert get_skill_similarity("Node.js", "nodejs") == 1.0
    assert get_skill_similarity("REST APIs", "REST") >= 0.75
    assert get_skill_similarity("PostgreSQL", "SQL") >= 0.60
    assert get_skill_similarity("Mongo", "MongoDB") >= 0.60
    assert get_skill_similarity("Java", "JavaScript") < 0.60

    corpus_match_map = build_skill_match_map(
        user_skills=["Java", "Mongo"],
        required_skills=[
            "Java",
            "JavaScript",
            "MongoDB",
            "Python",
            "TypeScript",
        ],
    )

    assert corpus_match_map["java"][0] == 1.0
    assert corpus_match_map["javascript"][0] == 0.0
    assert corpus_match_map["mongodb"][0] >= 0.60


def test_role_fit_uses_representative_jobs_instead_of_the_full_skill_union() -> None:
    jobs_df = pd.DataFrame(
        [
            make_job(
                "Backend Engineer",
                "Software Engineering",
                ["Python", "SQL", "Docker"],
            ),
            make_job(
                "Frontend Engineer",
                "Software Engineering",
                ["JavaScript", "React", "CSS"],
            ),
            make_job(
                "Systems Engineer",
                "Software Engineering",
                ["C++", "Linux", "Networking"],
            ),
            make_job(
                "Application Engineer",
                "Software Engineering",
                ["Java", "Spring", "Kubernetes"],
            ),
        ]
    )

    role_scores_df = score_roles(
        jobs_df,
        user_skills=["Python", "SQL", "Docker"],
    )

    software_row = role_scores_df.iloc[0]

    assert software_row["weighted_match_score"] == 100.0
    assert software_row["representative_job_count"] == 1
    assert software_row["sample_size"] == 4


def test_limited_sample_role_cannot_outrank_supported_role_for_headline() -> None:
    role_scores_df = pd.DataFrame(
        [
            {
                "role_category": "Cloud/AWS",
                "weighted_match_score": 100.0,
                "sample_size": 1,
                "headline_eligible": False,
            },
            {
                "role_category": "Software Engineering",
                "weighted_match_score": 45.0,
                "sample_size": 8,
                "headline_eligible": True,
            },
        ]
    )

    best_role_row = select_best_role_row(role_scores_df)

    assert best_role_row["role_category"] == "Software Engineering"


def test_canada_software_fit_is_monotonic_and_stable_when_linux_is_added() -> None:
    jobs_df = load_processed_jobs_from_csv(CANADA_SNAPSHOT_PATH)
    filtered_jobs_df = filter_jobs(
        df=jobs_df,
        target_roles=SOFTWARE_TARGET_ROLES,
        location="Any",
        experience_level="Any",
    )

    base_skills = ["Python", "REST APIs", "PostgreSQL", "Docker", "AWS"]
    expanded_skills = [
        *base_skills,
        "Java",
        "C#",
        "SQL",
        "Node.js",
    ]
    linux_skills = [*expanded_skills, "Linux"]

    base_scores = score_roles(filtered_jobs_df, base_skills)
    expanded_scores = score_roles(filtered_jobs_df, expanded_skills)
    linux_scores = score_roles(filtered_jobs_df, linux_skills)

    base_best = select_best_role_row(base_scores)
    expanded_best = select_best_role_row(expanded_scores)
    linux_best = select_best_role_row(linux_scores)

    assert base_best["role_category"] == "Software Engineering"
    assert expanded_best["role_category"] == "Software Engineering"
    assert linux_best["role_category"] == "Software Engineering"
    assert expanded_best["weighted_match_score"] > base_best["weighted_match_score"]
    assert linux_best["weighted_match_score"] >= expanded_best["weighted_match_score"]
    assert expanded_best["weighted_match_score"] - base_best["weighted_match_score"] >= 10
