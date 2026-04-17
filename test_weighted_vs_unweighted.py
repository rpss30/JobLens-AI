from src.processing.job_processor import process_jobs
from src.matching.match_engine import score_roles


df = process_jobs(
    input_path="data/raw/sample_jobs.csv",
    output_path="data/processed/processed_jobs.csv",
)

test_cases = [
    {
        "name": "Strong core data profile",
        "skills": ["Python", "SQL", "Pandas", "scikit-learn", "statistics"],
    },
    {
        "name": "Many lower-priority analytics tools",
        "skills": ["Excel", "Tableau", "Power BI", "documentation", "dashboards"],
    },
    {
        "name": "Strong cloud profile",
        "skills": ["AWS", "Docker", "Terraform", "Lambda", "S3", "CloudWatch"],
    },
    {
        "name": "Mixed resume profile",
        "skills": ["Python", "SQL", "AWS", "Pandas", "React", "Docker"],
    },
]

for case in test_cases:
    print(f"\n=== {case['name']} ===")
    print("Skills:", case["skills"])

    scores = score_roles(df, case["skills"])

    print(
        scores[
            [
                "role_category",
                "weighted_match_score",
                "unweighted_match_score",
                "matched_weight",
                "total_possible_weight",
            ]
        ]
    )

    score_diff = scores.copy()
    score_diff["difference"] = (
        score_diff["weighted_match_score"] - score_diff["unweighted_match_score"]
    )

    print("\nWeighted vs Unweighted Difference:")
    print(
        score_diff[
            [
                "role_category",
                "weighted_match_score",
                "unweighted_match_score",
                "difference",
            ]
        ]
    )