# test_match.py

from src.processing.job_processor import process_jobs
from src.matching.match_engine import get_top_skills, score_roles


df = process_jobs(
    input_path="data/raw/sample_jobs.csv",
    output_path="data/processed/processed_jobs.csv",
)

user_skills = ["Python", "SQL", "AWS", "React", "Pandas"]

print("\nTop Skills:")
print(get_top_skills(df, top_n=10))

print("\nRole Match Scores:")
print(score_roles(df, user_skills))