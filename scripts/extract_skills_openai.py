"""Optional LLM-assisted skill extraction experiment.

This script samples real Adzuna jobs and asks OpenAI to extract technical
skills as structured JSON. It does not replace the default deterministic
JobLens processor.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import AuthenticationError, OpenAI, OpenAIError, RateLimitError

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

INPUT_PATH = ROOT_DIR / "data" / "raw" / "adzuna_jobs.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "openai_skill_extraction_sample.csv"

MODEL_NAME = "gpt-4.1-mini"


SKILL_EXTRACTION_SCHEMA = {
    "name": "job_skill_extraction",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "technical_skills": {
                "type": "array",
                "items": {"type": "string"},
            },
            "tools_and_platforms": {
                "type": "array",
                "items": {"type": "string"},
            },
            "programming_languages": {
                "type": "array",
                "items": {"type": "string"},
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
        },
        "required": [
            "technical_skills",
            "tools_and_platforms",
            "programming_languages",
            "confidence",
        ],
    },
}


def get_client() -> OpenAI:
    """Create an OpenAI client using the local .env file."""
    load_dotenv(dotenv_path=ROOT_DIR / ".env")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in local .env file.")

    return OpenAI(api_key=api_key)


def extract_skills_with_openai(client: OpenAI, title: str, description: str) -> dict:
    """Extract technical skills from one job posting using structured output."""
    prompt = f"""
Extract technical skills from this job posting.

Rules:
- Extract only concrete technical skills, tools, platforms, programming languages, frameworks, libraries, databases, cloud services, and ML/data concepts.
- Do not include soft skills.
- Do not include generic words like team, communication, business, platform, customer, work, experience, or leadership.
- Use normalized names where possible, such as Python, SQL, AWS, PostgreSQL, PyTorch, TensorFlow, Docker, Kubernetes, Terraform, REST APIs.
- If no concrete technical skills are present, return empty arrays.
- Keep each skill short.

Job title:
{title}

Job description:
{description[:4000]}
""".strip()

    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {
                "role": "system",
                "content": "You extract structured technical skills from job postings.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": SKILL_EXTRACTION_SCHEMA["name"],
                "schema": SKILL_EXTRACTION_SCHEMA["schema"],
                "strict": True,
            }
        },
    )

    return json.loads(response.output_text)


def main(sample_size: int = 10) -> None:
    """Run LLM-assisted extraction on a small sample of Adzuna jobs."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run scripts/fetch_adzuna_jobs.py first."
        )

    jobs_df = pd.read_csv(INPUT_PATH).head(sample_size)
    client = get_client()

    rows = []

    for index, row in jobs_df.iterrows():
        title = str(row.get("title", ""))
        company = str(row.get("company", ""))
        location = str(row.get("location", ""))
        description = str(row.get("description", ""))

        print(f"Extracting skills for {index + 1}/{len(jobs_df)}: {title} - {company}")

        try:
            extracted = extract_skills_with_openai(
                client=client,
                title=title,
                description=description,
            )
        except AuthenticationError:
            print("OpenAI authentication failed. Check OPENAI_API_KEY in your local .env file.")
            break
        except RateLimitError as error:
            print(f"OpenAI quota or rate limit error: {error}")
            print("Stopping extraction so the script does not keep retrying paid API calls.")
            break
        except OpenAIError as error:
            print(f"OpenAI API error: {error}")
            break

        rows.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "openai_technical_skills": extracted["technical_skills"],
                "openai_tools_and_platforms": extracted["tools_and_platforms"],
                "openai_programming_languages": extracted["programming_languages"],
                "openai_confidence": extracted["confidence"],
            }
        )

    output_df = pd.DataFrame(rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved OpenAI extraction sample to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()