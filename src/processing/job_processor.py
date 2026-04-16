# src/processing/job_processor.py

import re
import pandas as pd
from src.config.skills import TECH_SKILLS


def normalize_text(text: str) -> str:
    """Convert text to lowercase and remove extra spaces."""
    if pd.isna(text):
        return ""

    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_skills(description: str) -> list[str]:
    """Extract known technical skills from a job description."""
    description = normalize_text(description)
    found_skills = []

    for skill in TECH_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, description):
            found_skills.append(skill)

    return found_skills


def categorize_role(title: str, description: str) -> str:
    """Assign a simple role category based on title and description."""
    text = normalize_text(title + " " + description)

    if any(word in text for word in ["machine learning", "ml engineer", "ai engineer", "pytorch", "tensorflow", "nlp"]):
        return "AI/ML"

    if any(word in text for word in ["data scientist", "statistics", "scikit-learn", "model"]):
        return "Data Science"

    if any(word in text for word in ["data engineer", "etl", "spark", "airflow", "data warehouse"]):
        return "Data Engineering"

    if any(word in text for word in ["cloud", "aws", "lambda", "ec2", "s3", "terraform"]):
        return "Cloud/AWS"

    if any(word in text for word in ["backend", "software engineer", "rest api", "java", "node"]):
        return "Software Engineering"

    if any(word in text for word in ["analyst", "tableau", "power bi", "dashboard", "business"]):
        return "Analytics"

    return "Other"


def process_jobs(input_path: str, output_path: str) -> pd.DataFrame:
    """Load raw jobs, extract skills/categories, and save processed data."""
    df = pd.read_csv(input_path)

    df["clean_title"] = df["title"].apply(normalize_text)
    df["clean_description"] = df["description"].apply(normalize_text)

    df["extracted_skills"] = df["description"].apply(extract_skills)
    df["role_category"] = df.apply(
        lambda row: categorize_role(row["title"], row["description"]),
        axis=1,
    )

    # Save list column as comma-separated text for CSV output.
    df["skills_text"] = df["extracted_skills"].apply(lambda skills: ", ".join(skills))

    df.to_csv(output_path, index=False)
    return df


if __name__ == "__main__":
    processed_df = process_jobs(
        input_path="data/raw/sample_jobs.csv",
        output_path="data/processed/processed_jobs.csv",
    )

    print(processed_df[["title", "role_category", "skills_text"]])