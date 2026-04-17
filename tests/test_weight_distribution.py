from src.processing.job_processor import process_jobs
from src.matching.match_engine import build_role_skill_weights


df = process_jobs(
    input_path="data/raw/sample_jobs.csv",
    output_path="data/processed/processed_jobs.csv",
)

role_weights = build_role_skill_weights(df)

print("\nROLE WEIGHT DISTRIBUTION TEST")

for role_category, weights in role_weights.items():
    print(f"\n=== {role_category} ===")
    print(f"Number of skills: {len(weights)}")

    weight_counts = {}
    for weight in weights.values():
        weight_counts[weight] = weight_counts.get(weight, 0) + 1

    print("Weight distribution:", dict(sorted(weight_counts.items())))

    sorted_skills = sorted(
        weights.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    print("Top weighted skills:")
    for skill, weight in sorted_skills[:10]:
        print(f"  {skill}: {weight}")