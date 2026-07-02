"""Privacy-conscious resume analysis for role-fit matching.

The module intentionally avoids storing resume text. Callers pass pasted text in,
receive deterministic extracted signals, and can discard the raw text immediately.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.config.skills import BASE_SKILL_IMPORTANCE, TECH_SKILLS
from src.matching.match_engine import (
    build_role_skill_weights,
    build_skill_match_map,
    normalize_skill,
    score_roles,
    score_skill_set,
    select_best_role_row,
)
from src.search.semantic_search import rank_jobs_by_candidate_profile


MAX_RESUME_TEXT_LENGTH = 12_000
PRIVACY_NOTE = (
    "Resume text is analyzed in memory for this request and is not persisted "
    "to PostgreSQL or saved analysis history."
)


SKILL_ALIASES: dict[str, list[str]] = {
    "a/b testing": ["a/b testing", "ab testing", "experimentation"],
    "airflow": ["airflow", "apache airflow"],
    "api gateway": ["api gateway", "aws api gateway"],
    "aws": ["aws", "amazon web services"],
    "ci/cd": ["ci/cd", "ci cd", "continuous integration", "continuous deployment"],
    "cloudwatch": ["cloudwatch", "amazon cloudwatch"],
    "data pipelines": ["data pipeline", "data pipelines", "etl pipeline", "etl pipelines"],
    "dbt": ["dbt", "data build tool"],
    "docker": ["docker", "containerization", "containers"],
    "ec2": ["ec2", "amazon ec2"],
    "embeddings": ["embeddings", "embedding search", "semantic search"],
    "kubernetes": ["kubernetes", "k8s"],
    "lambda": ["lambda", "aws lambda"],
    "machine learning": ["machine learning", "ml"],
    "model deployment": ["model deployment", "model serving", "deploy models"],
    "model monitoring": ["model monitoring", "monitoring models"],
    "mysql": ["mysql", "my sql"],
    "node.js": ["node.js", "nodejs", "node js", "node"],
    "postgresql": ["postgresql", "postgres", "postgre sql"],
    "power bi": ["power bi", "powerbi"],
    "pyspark": ["pyspark", "py spark"],
    "rest apis": ["rest api", "rest apis", "api development", "api design"],
    "s3": ["s3", "amazon s3"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "tableau": ["tableau"],
    "tensorflow": ["tensorflow", "tensor flow"],
    "typescript": ["typescript", "type script"],
    "vector databases": ["vector database", "vector databases", "pgvector"],
}


EXPERIENCE_AREA_PATTERNS: dict[str, list[str]] = {
    "backend engineering": [
        "api",
        "backend",
        "microservice",
        "service",
        "server",
    ],
    "cloud/devops": [
        "aws",
        "cloud",
        "docker",
        "infrastructure",
        "kubernetes",
        "terraform",
    ],
    "data engineering": [
        "airflow",
        "data pipeline",
        "etl",
        "spark",
        "warehouse",
    ],
    "data analytics": [
        "analytics",
        "dashboard",
        "metrics",
        "power bi",
        "sql",
        "tableau",
    ],
    "machine learning": [
        "embedding",
        "machine learning",
        "ml",
        "model",
        "pytorch",
        "tensorflow",
    ],
    "frontend engineering": [
        "frontend",
        "react",
        "typescript",
        "ui",
    ],
}


PROJECT_KEYWORD_PATTERNS: dict[str, list[str]] = {
    "api development": ["api", "endpoint", "fastapi", "rest"],
    "automation": ["automation", "script", "workflow"],
    "dashboarding": ["dashboard", "visualization", "reporting"],
    "data pipelines": ["airflow", "etl", "pipeline"],
    "deployment": ["deploy", "deployment", "docker", "ecs"],
    "experimentation": ["a/b", "experiment", "hypothesis"],
    "modeling": ["classification", "forecast", "model", "prediction"],
    "monitoring": ["alert", "logging", "monitoring", "observability"],
}


@dataclass(frozen=True)
class ResumeAnalysisConfig:
    top_jobs: int = 5
    learning_priorities: int = 6
    suggested_keywords: int = 8


DEFAULT_RESUME_ANALYSIS_CONFIG = ResumeAnalysisConfig()


def clean_resume_text(resume_text: str, max_length: int = MAX_RESUME_TEXT_LENGTH) -> str:
    """Normalize whitespace and bound pasted resume text for analysis."""
    cleaned_text = re.sub(r"\s+", " ", str(resume_text or "")).strip()
    return cleaned_text[:max_length]


def normalize_resume_text(resume_text: str) -> str:
    return normalize_skill(clean_resume_text(resume_text))


def get_resume_skill_taxonomy() -> list[str]:
    preferred_names: dict[str, str] = {}

    for skill in [*TECH_SKILLS, *BASE_SKILL_IMPORTANCE.keys(), *SKILL_ALIASES.keys()]:
        normalized_skill = normalize_skill(skill)

        if normalized_skill and normalized_skill not in preferred_names:
            preferred_names[normalized_skill] = str(skill).strip().lower()

    return sorted(preferred_names.values())


def build_alias_lookup() -> dict[str, list[str]]:
    alias_lookup: dict[str, list[str]] = {}

    for skill in get_resume_skill_taxonomy():
        aliases = {skill, *SKILL_ALIASES.get(skill, [])}
        normalized_aliases = {
            normalize_skill(alias)
            for alias in aliases
            if normalize_skill(alias)
        }
        alias_lookup[skill] = sorted(normalized_aliases, key=lambda value: (-len(value), value))

    return alias_lookup


def canonicalize_resume_skill(skill: str) -> str:
    normalized_skill = normalize_skill(skill)

    if not normalized_skill:
        return ""

    for canonical_skill, aliases in build_alias_lookup().items():
        if normalized_skill in aliases:
            return canonical_skill

    return normalized_skill


def phrase_in_text(phrase: str, normalized_text: str) -> bool:
    if not phrase or not normalized_text:
        return False

    phrase_pattern = r"\s+".join(re.escape(part) for part in phrase.split())
    return bool(
        re.search(
            rf"(?<![a-z0-9+#]){phrase_pattern}(?![a-z0-9+#])",
            normalized_text,
        )
    )


def extract_resume_skills(resume_text: str) -> list[str]:
    """Extract known JobLens skills from pasted resume text."""
    normalized_text = normalize_resume_text(resume_text)

    if not normalized_text:
        return []

    detected_skills = []

    for skill, aliases in build_alias_lookup().items():
        if any(phrase_in_text(alias, normalized_text) for alias in aliases):
            detected_skills.append(skill)

    return sorted(
        detected_skills,
        key=lambda skill: (-BASE_SKILL_IMPORTANCE.get(skill, 1), skill),
    )


def extract_pattern_matches(
    resume_text: str,
    pattern_groups: dict[str, list[str]],
    limit: int,
) -> list[str]:
    normalized_text = normalize_resume_text(resume_text)

    if not normalized_text:
        return []

    matches: list[tuple[str, int]] = []

    for label, patterns in pattern_groups.items():
        match_count = sum(
            1
            for pattern in patterns
            if phrase_in_text(normalize_skill(pattern), normalized_text)
        )

        if match_count:
            matches.append((label, match_count))

    return [
        label
        for label, _ in sorted(matches, key=lambda item: (-item[1], item[0]))[:limit]
    ]


def merge_candidate_skills(
    current_skills: list[str],
    resume_skills: list[str],
) -> list[str]:
    merged_skills: list[str] = []
    seen_skills: set[str] = set()

    for skill in [*current_skills, *resume_skills]:
        canonical_skill = canonicalize_resume_skill(skill)
        normalized_skill = normalize_skill(canonical_skill)

        if normalized_skill and normalized_skill not in seen_skills:
            seen_skills.add(normalized_skill)
            merged_skills.append(canonical_skill)

    return merged_skills


def get_market_skill_counts(jobs_df: pd.DataFrame) -> Counter[str]:
    skill_counts: Counter[str] = Counter()

    if "extracted_skills" not in jobs_df.columns:
        return skill_counts

    for skills in jobs_df["extracted_skills"]:
        if not isinstance(skills, list):
            continue

        for skill in skills:
            normalized_skill = normalize_skill(skill)

            if normalized_skill:
                skill_counts[normalized_skill] += 1

    return skill_counts


def build_learning_priorities(
    *,
    missing_skills: list[str],
    jobs_df: pd.DataFrame,
    limit: int,
) -> list[dict[str, Any]]:
    market_skill_counts = get_market_skill_counts(jobs_df)
    priorities = []

    for skill in missing_skills:
        normalized_skill = normalize_skill(skill)

        if not normalized_skill:
            continue

        demand_count = market_skill_counts.get(normalized_skill, 0)
        importance = BASE_SKILL_IMPORTANCE.get(normalized_skill, 1)
        priority_score = (importance * 10) + demand_count
        priorities.append({
            "skill": normalized_skill,
            "priority_score": float(priority_score),
            "job_count": int(demand_count),
            "reason": (
                f"Appears in {demand_count} matching postings and has "
                f"{importance}/5 baseline importance."
            ),
        })

    return sorted(
        priorities,
        key=lambda row: (-row["priority_score"], row["skill"]),
    )[:limit]


def build_suggested_resume_keywords(
    *,
    jobs_df: pd.DataFrame,
    candidate_skills: list[str],
    limit: int,
) -> list[str]:
    candidate_skill_set = {
        normalize_skill(skill)
        for skill in candidate_skills
        if normalize_skill(skill)
    }
    skill_counts = get_market_skill_counts(jobs_df)

    candidate_keywords = [
        skill
        for skill, _ in skill_counts.most_common()
        if skill not in candidate_skill_set
    ]

    return candidate_keywords[:limit]


def build_job_match_rows(
    *,
    jobs_df: pd.DataFrame,
    candidate_skills: list[str],
    resume_text: str,
    target_roles: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    if jobs_df.empty:
        return []

    role_skill_weights = build_role_skill_weights(jobs_df)
    ranked_jobs = rank_jobs_by_candidate_profile(
        jobs_df,
        current_skills=candidate_skills,
        resume_text=resume_text,
        target_roles=target_roles,
    )
    required_skills = sorted({
        normalize_skill(skill)
        for skills in ranked_jobs.get("extracted_skills", [])
        if isinstance(skills, list)
        for skill in skills
        if normalize_skill(skill)
    })
    skill_match_map = build_skill_match_map(candidate_skills, required_skills)
    job_rows = []

    for _, job in ranked_jobs.head(limit).iterrows():
        job_required_skills = (
            job["extracted_skills"]
            if isinstance(job.get("extracted_skills"), list)
            else []
        )
        role_category = str(job.get("role_category", "Other"))
        skill_score = score_skill_set(
            required_skills=job_required_skills,
            role_category=role_category,
            role_skill_weights=role_skill_weights,
            skill_match_map=skill_match_map,
        )
        resume_similarity = float(job.get("resume_similarity", 0.0))
        skill_fit_score = float(skill_score["weighted_match_score"])
        fit_score = round((skill_fit_score * 0.75) + (resume_similarity * 0.25), 1)
        matched_skills = list(skill_score["matched_skills"])[:6]
        missing_skills = list(skill_score["missing_skills"])[:6]

        if matched_skills and missing_skills:
            explanation = (
                f"Matches {', '.join(matched_skills[:3])}; strongest gaps are "
                f"{', '.join(missing_skills[:3])}."
            )
        elif matched_skills:
            explanation = f"Strong overlap on {', '.join(matched_skills[:3])}."
        elif missing_skills:
            explanation = f"Limited skill overlap; review {', '.join(missing_skills[:3])}."
        else:
            explanation = "This posting has limited extracted skill data."

        job_rows.append({
            "title": str(job.get("title", "")),
            "company": str(job.get("company", "")),
            "location": str(job.get("location", "")),
            "role_category": role_category,
            "fit_score": fit_score,
            "skill_fit_score": round(skill_fit_score, 1),
            "resume_similarity": round(resume_similarity, 1),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "explanation": explanation,
        })

    return sorted(job_rows, key=lambda row: row["fit_score"], reverse=True)


def analyze_resume_against_jobs(
    *,
    jobs_df: pd.DataFrame,
    resume_text: str,
    current_skills: list[str] | None = None,
    target_roles: list[str] | None = None,
    config: ResumeAnalysisConfig = DEFAULT_RESUME_ANALYSIS_CONFIG,
) -> dict[str, Any]:
    """Analyze pasted resume text against a filtered JobLens job dataset."""
    cleaned_resume_text = clean_resume_text(resume_text)
    resume_skills = extract_resume_skills(cleaned_resume_text)
    candidate_skills = merge_candidate_skills(current_skills or [], resume_skills)
    target_roles = target_roles or []
    experience_areas = extract_pattern_matches(
        cleaned_resume_text,
        EXPERIENCE_AREA_PATTERNS,
        limit=5,
    )
    project_keywords = extract_pattern_matches(
        cleaned_resume_text,
        PROJECT_KEYWORD_PATTERNS,
        limit=6,
    )

    if jobs_df.empty or not candidate_skills:
        return {
            "provided": bool(cleaned_resume_text),
            "privacy_note": PRIVACY_NOTE,
            "resume_skills": resume_skills,
            "combined_skills": candidate_skills,
            "experience_areas": experience_areas,
            "project_keywords": project_keywords,
            "fit_score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "learning_priorities": [],
            "suggested_resume_keywords": [],
            "top_matching_jobs": [],
            "explanation": (
                "Add resume text or current skills to generate a resume match."
                if not candidate_skills
                else "No matching jobs were available for resume comparison."
            ),
        }

    role_scores_df = score_roles(jobs_df, candidate_skills)
    best_role_row = select_best_role_row(role_scores_df) if not role_scores_df.empty else pd.Series(dtype=object)
    fit_score = float(best_role_row.get("weighted_match_score", 0.0))
    matched_skills = list(best_role_row.get("matched_skills", []))[:8]
    missing_skills = list(best_role_row.get("missing_skills", []))[:8]
    top_role = str(best_role_row.get("role_category", "No match"))
    job_rows = build_job_match_rows(
        jobs_df=jobs_df,
        candidate_skills=candidate_skills,
        resume_text=cleaned_resume_text,
        target_roles=target_roles,
        limit=config.top_jobs,
    )
    suggested_keywords = build_suggested_resume_keywords(
        jobs_df=jobs_df,
        candidate_skills=candidate_skills,
        limit=config.suggested_keywords,
    )
    learning_priorities = build_learning_priorities(
        missing_skills=missing_skills or suggested_keywords,
        jobs_df=jobs_df,
        limit=config.learning_priorities,
    )

    if fit_score > 0:
        explanation = (
            f"Your resume profile is strongest for {top_role} with "
            f"{fit_score:.1f}% weighted skill fit across the current job set."
        )
    else:
        explanation = (
            "JobLens found limited overlap between the resume profile and the "
            "current job set; use the missing skills as learning priorities."
        )

    return {
        "provided": bool(cleaned_resume_text),
        "privacy_note": PRIVACY_NOTE,
        "resume_skills": resume_skills,
        "combined_skills": candidate_skills,
        "experience_areas": experience_areas,
        "project_keywords": project_keywords,
        "fit_score": round(fit_score, 1),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "learning_priorities": learning_priorities,
        "suggested_resume_keywords": suggested_keywords,
        "top_matching_jobs": job_rows,
        "explanation": explanation,
    }
