# src/processing/job_processor.py

import re
import pandas as pd
from src.config.skills import TECH_SKILLS

RAW_JOB_REQUIRED_COLUMNS = [
    "title",
    "company",
    "location",
    "description",
    "experience_level",
]

PROCESSED_JOB_REQUIRED_COLUMNS = [
    "title",
    "company",
    "location",
    "description",
    "experience_level",
    "clean_title",
    "clean_description",
    "extracted_skills",
    "role_category",
    "skills_text",
]

def validate_required_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    schema_name: str,
) -> None:
    """Raise a clear error if a dataframe is missing required columns."""
    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{schema_name} is missing required columns: {missing_columns}"
        )

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
    """Assign a role category using title first, then description."""
    title_text = normalize_text(title)
    full_text = normalize_text(title + " " + description)

    # Title-based rules first because they are more reliable.
    if any(word in title_text for word in ["machine learning", "ml engineer", "ml platform", "ai engineer"]):
        return "AI/ML"

    if "data scientist" in title_text:
        return "Data Science"

    if "data engineer" in title_text:
        return "Data Engineering"

    if any(word in title_text for word in ["cloud engineer", "aws cloud", "devops", "platform engineer", "cloud developer"]):
        return "Cloud/AWS"

    if any(word in title_text for word in ["backend developer", "backend engineer", "software engineer", "full stack developer", "developer"]):
        return "Software Engineering"

    if any(word in title_text for word in ["analyst", "business intelligence", "product analyst"]):
        return "Analytics"

    # Fallback description-based rules.
    if any(word in full_text for word in ["machine learning", "pytorch", "tensorflow", "nlp", "embeddings"]):
        return "AI/ML"

    if any(word in full_text for word in ["data scientist", "statistics", "scikit-learn"]):
        return "Data Science"

    if any(word in full_text for word in ["data engineer", "etl", "spark", "airflow", "data warehouse"]):
        return "Data Engineering"

    if any(word in full_text for word in ["cloud", "aws", "lambda", "ec2", "s3", "terraform"]):
        return "Cloud/AWS"

    if any(word in full_text for word in ["backend", "software engineer", "rest api", "java", "node"]):
        return "Software Engineering"

    if any(word in full_text for word in ["analyst", "tableau", "power bi", "dashboard", "business"]):
        return "Analytics"

    return "Other"


def process_jobs(input_path: str, output_path: str) -> pd.DataFrame:
    """Load raw jobs, extract skills/categories, validate schema, and save processed data."""
    df = pd.read_csv(input_path)

    validate_required_columns(
        df=df,
        required_columns=RAW_JOB_REQUIRED_COLUMNS,
        schema_name="Raw jobs dataframe",
    )

    df["clean_title"] = df["title"].apply(normalize_text)
    df["clean_description"] = df["description"].apply(normalize_text)

    df["extracted_skills"] = df["description"].apply(extract_skills)
    df["role_category"] = df.apply(
        lambda row: categorize_role(row["title"], row["description"]),
        axis=1,
    )

    # Save list column as comma-separated text for CSV output.
    df["skills_text"] = df["extracted_skills"].apply(lambda skills: ", ".join(skills))

    validate_required_columns(
        df=df,
        required_columns=PROCESSED_JOB_REQUIRED_COLUMNS,
        schema_name="Processed jobs dataframe",
    )

    df.to_csv(output_path, index=False)
    return df


if __name__ == "__main__":
    processed_df = process_jobs(
        input_path="data/raw/sample_jobs.csv",
        output_path="data/processed/processed_jobs.csv",
    )

    print(processed_df[["title", "role_category", "skills_text"]])