from src.processing.job_processor import process_jobs
from src.matching.match_engine import score_roles, build_role_skill_weights

df = process_jobs(
    input_path="data/raw/sample_jobs.csv",
    output_path="data/processed/processed_jobs.csv",
)

test_profiles = {
    "Data Science Profile": [
        "Python", "SQL", "Pandas", "scikit-learn", "statistics", "data visualization"
    ],
    "Cloud AWS Profile": [
        "AWS", "S3", "Lambda", "EC2", "Docker", "Terraform", "CloudWatch", "CI/CD"
    ],
    "AI ML Profile": [
        "Python", "PyTorch", "TensorFlow", "NLP", "embeddings", "Docker", "model deployment", "MLflow"
    ],
    "Backend Profile": [
        "Python", "Java", "SQL", "REST APIs", "PostgreSQL", "Docker", "AWS"
    ],
    "Analytics Profile": [
        "SQL", "Python", "Tableau", "Power BI", "Excel", "A/B testing", "data visualization"
    ],
    "Basic Frontend Profile": [
        "HTML", "CSS", "React", "JavaScript"
    ],
    "Empty Profile": [],
}

print("\nROLE-SPECIFIC SKILL WEIGHTS")
role_weights = build_role_skill_weights(df)

for role, weights in role_weights.items():
    print(f"\n{role}")
    sorted_weights = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    print(sorted_weights)

print("\nMATCH SCORE TESTS")

for profile_name, skills in test_profiles.items():
    print(f"\n=== {profile_name} ===")
    print(f"Skills: {skills}")

    scores = score_roles(df, skills)

    print(
        scores[
            [
                "role_category",
                "sample_size",
                "weighted_match_score",
                "unweighted_match_score",
                "matched_weight",
                "total_possible_weight",
            ]
        ]
    )