# src/matching/match_engine.py

import math
import re
from collections import defaultdict

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


RELATED_SKILL_THRESHOLD = 0.60
REPRESENTATIVE_JOB_QUANTILE = 0.25
MIN_HEADLINE_CONFIDENCE = 0.45
CONFIDENCE_SAMPLE_SCALE = 5.0

def normalize_skill(skill: str) -> str:
    """Normalize skill names for comparison."""
    normalized = str(skill).strip().lower()
    normalized = re.sub(r"(?<=\w)\.(?=\w)", "", normalized)
    normalized = re.sub(r"[-_/]+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9+#\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    tokens = [
        "api" if token == "apis" else token
        for token in normalized.split()
    ]

    return " ".join(tokens)


def _lexical_skill_similarity(first_skill: str, second_skill: str) -> float:
    """Estimate structured lexical overlap between two normalized skills."""
    if not first_skill or not second_skill:
        return 0.0

    if first_skill == second_skill:
        return 1.0

    first_tokens = set(first_skill.split())
    second_tokens = set(second_skill.split())
    shared_tokens = first_tokens.intersection(second_tokens)

    similarity = 0.0

    if shared_tokens:
        if first_tokens.issubset(second_tokens) or second_tokens.issubset(first_tokens):
            coverage = len(shared_tokens) / max(len(first_tokens), len(second_tokens))
            similarity = max(similarity, 0.75 + (0.15 * coverage))
        else:
            union_size = len(first_tokens.union(second_tokens))
            similarity = max(
                similarity,
                0.55 + (0.20 * len(shared_tokens) / union_size),
            )

    first_compact = first_skill.replace(" ", "")
    second_compact = second_skill.replace(" ", "")
    shorter, longer = sorted(
        [first_compact, second_compact],
        key=len,
    )

    if len(shorter) >= 3 and longer.endswith(shorter):
        similarity = max(similarity, 0.70)

    return min(similarity, 1.0)


def build_skill_match_map(
    user_skills: list[str],
    required_skills: list[str],
) -> dict[str, tuple[float, str | None]]:
    """
    Match required skills to the closest candidate skill.

    Character n-gram TF-IDF handles spelling and formatting variants while
    conservative lexical overlap captures compound skills such as REST APIs.
    """
    normalized_user_skills = sorted({
        normalize_skill(skill)
        for skill in user_skills
        if normalize_skill(skill)
    })
    normalized_required_skills = sorted({
        normalize_skill(skill)
        for skill in required_skills
        if normalize_skill(skill)
    })

    if not normalized_required_skills:
        return {}

    if not normalized_user_skills:
        return {
            required_skill: (0.0, None)
            for required_skill in normalized_required_skills
        }

    all_skills = normalized_user_skills + normalized_required_skills
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 5),
        lowercase=False,
    )
    skill_matrix = vectorizer.fit_transform(all_skills)
    user_matrix = skill_matrix[:len(normalized_user_skills)]
    required_matrix = skill_matrix[len(normalized_user_skills):]
    character_similarities = cosine_similarity(required_matrix, user_matrix)

    match_map: dict[str, tuple[float, str | None]] = {}

    for required_index, required_skill in enumerate(normalized_required_skills):
        best_quality = 0.0
        best_user_skill = None

        for user_index, user_skill in enumerate(normalized_user_skills):
            character_similarity = float(
                character_similarities[required_index, user_index]
            )
            lexical_similarity = _lexical_skill_similarity(
                required_skill,
                user_skill,
            )

            required_compact = required_skill.replace(" ", "")
            user_compact = user_skill.replace(" ", "")
            shorter, longer = sorted(
                [required_compact, user_compact],
                key=len,
            )
            prefix_similarity = (
                0.70
                if (
                    len(shorter) >= 4
                    and longer.startswith(shorter)
                    and character_similarity >= 0.40
                )
                else 0.0
            )
            match_quality = max(character_similarity, lexical_similarity)
            match_quality = max(match_quality, prefix_similarity)

            if match_quality > best_quality:
                best_quality = match_quality
                best_user_skill = user_skill

        if best_quality < RELATED_SKILL_THRESHOLD:
            best_quality = 0.0
            best_user_skill = None

        match_map[required_skill] = (
            round(min(best_quality, 1.0), 4),
            best_user_skill,
        )

    return match_map


def get_skill_similarity(first_skill: str, second_skill: str) -> float:
    """Return the similarity between two skill names on a zero-to-one scale."""
    normalized_second_skill = normalize_skill(second_skill)
    match_map = build_skill_match_map(
        user_skills=[first_skill],
        required_skills=[second_skill],
    )

    return match_map.get(normalized_second_skill, (0.0, None))[0]

def frequency_to_weight(frequency: float) -> int:
    """Convert skill frequency into an importance weight from 1 to 5."""
    if frequency >= 0.75:
        return 5
    if frequency >= 0.50:
        return 4
    if frequency >= 0.30:
        return 3
    if frequency >= 0.15:
        return 2
    return 1

def get_max_weight_for_sample_size(total_jobs: int) -> int:
    """Limit max skill weight when a role category has too few jobs."""
    if total_jobs <= 2:
        return 3
    if total_jobs <= 4:
        return 4
    return 5

def build_role_skill_weights(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """
    Build role-specific skill weights using TF-IDF over extracted skills.

    Each role category is treated like a document, and each extracted skill is
    treated like a term. Skills that are common within a role but less common
    across other roles receive stronger role-specific weights.

    Example output:
    {
        "AI/ML": {"python": 4, "pytorch": 5, "docker": 2},
        "Cloud/AWS": {"aws": 5, "terraform": 4, "python": 1}
    }
    """
    if df.empty or "role_category" not in df.columns or "extracted_skills" not in df.columns:
        return {}

    role_documents: dict[str, str] = {}
    role_sample_sizes: dict[str, int] = {}

    for role_category, group in df.groupby("role_category"):
        role_sample_sizes[role_category] = len(group)

        role_skill_terms: list[str] = []

        for skills in group["extracted_skills"]:
            if not isinstance(skills, list):
                continue

            # Count each skill at most once per job posting.
            unique_skills = sorted({normalize_skill(skill) for skill in skills})

            # Replace spaces with underscores so multi-word skills stay together.
            role_skill_terms.extend(skill.replace(" ", "_") for skill in unique_skills)

        if role_skill_terms:
            role_documents[role_category] = " ".join(role_skill_terms)

    if not role_documents:
        return {}

    role_categories = list(role_documents.keys())
    documents = [role_documents[role_category] for role_category in role_categories]

    vectorizer = TfidfVectorizer(
        lowercase=False,
        tokenizer=str.split,
        preprocessor=None,
        token_pattern=None,
    )

    tfidf_matrix = vectorizer.fit_transform(documents)
    feature_names = vectorizer.get_feature_names_out()

    role_weights: dict[str, dict[str, int]] = {}

    for role_index, role_category in enumerate(role_categories):
        row = tfidf_matrix[role_index].toarray()[0]
        max_score = row.max()

        max_weight = get_max_weight_for_sample_size(
            role_sample_sizes.get(role_category, 0)
        )

        weights: dict[str, int] = {}

        if max_score == 0:
            role_weights[role_category] = weights
            continue

        for skill_token, tfidf_score in zip(feature_names, row):
            if tfidf_score == 0:
                continue

            skill = skill_token.replace("_", " ")

            # Normalize TF-IDF to the dashboard's readable 1-5 weight scale.
            scaled_weight = round(1 + 4 * (tfidf_score / max_score))
            weights[skill] = min(max(scaled_weight, 1), max_weight)

        role_weights[role_category] = weights

    return role_weights

def get_skill_weight_for_role(
    skill: str,
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> int:
    """Get a skill's weight for a specific role category."""
    normalized_skill = normalize_skill(skill)

    return role_skill_weights.get(role_category, {}).get(normalized_skill, 1)


def calculate_role_match_score(
    user_skills: list[str],
    required_skills: list[str],
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> tuple[float, int, int]:
    """Calculate weighted role match score for one role category."""
    if not required_skills:
        return 0.0, 0, 0

    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    total_possible_weight = sum(
        get_skill_weight_for_role(skill, role_category, role_skill_weights)
        for skill in required_skill_set
    )

    matched_weight = sum(
        get_skill_weight_for_role(skill, role_category, role_skill_weights)
        for skill in required_skill_set
        if skill in user_skill_set
    )

    if total_possible_weight == 0:
        return 0.0, matched_weight, total_possible_weight

    score = round((matched_weight / total_possible_weight) * 100, 2)

    return score, matched_weight, total_possible_weight


def calculate_unweighted_match_score(
    user_skills: list[str],
    required_skills: list[str],
) -> float:
    """Calculate simple percentage score for comparison."""
    if not required_skills:
        return 0.0

    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    matched_skills = user_skill_set.intersection(required_skill_set)

    return round((len(matched_skills) / len(required_skill_set)) * 100, 2)


def get_matched_skills(
    user_skills: list[str],
    required_skills: list[str],
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> list[str]:
    """Return matched skills sorted by role-specific importance."""
    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    matched = user_skill_set.intersection(required_skill_set)

    return sorted(
        matched,
        key=lambda skill: get_skill_weight_for_role(
            skill,
            role_category,
            role_skill_weights,
        ),
        reverse=True,
    )


def get_missing_skills(
    user_skills: list[str],
    required_skills: list[str],
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> list[str]:
    """Return missing skills sorted by role-specific importance."""
    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    missing = required_skill_set - user_skill_set

    return sorted(
        missing,
        key=lambda skill: get_skill_weight_for_role(
            skill,
            role_category,
            role_skill_weights,
        ),
        reverse=True,
    )


def score_skill_set(
    required_skills: list[str],
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
    skill_match_map: dict[str, tuple[float, str | None]],
) -> dict:
    """Score one posting's extracted skills against a candidate profile."""
    normalized_required_skills = sorted({
        normalize_skill(skill)
        for skill in required_skills
        if normalize_skill(skill)
    })

    if not normalized_required_skills:
        return {
            "weighted_match_score": 0.0,
            "unweighted_match_score": 0.0,
            "matched_weight": 0.0,
            "total_possible_weight": 0.0,
            "matched_skills": [],
            "related_skills": [],
            "missing_skills": [],
            "skill_match_details": [],
        }

    matched_weight = 0.0
    total_possible_weight = 0.0
    match_quality_total = 0.0
    matched_skills = []
    related_skills = []
    missing_skills = []
    skill_match_details = []

    for required_skill in normalized_required_skills:
        skill_weight = float(
            get_skill_weight_for_role(
                required_skill,
                role_category,
                role_skill_weights,
            )
        )
        match_quality, matched_user_skill = skill_match_map.get(
            required_skill,
            (0.0, None),
        )

        total_possible_weight += skill_weight
        matched_weight += skill_weight * match_quality
        match_quality_total += match_quality

        if match_quality >= RELATED_SKILL_THRESHOLD and matched_user_skill:
            matched_skills.append(required_skill)

            if match_quality < 1.0:
                related_skills.append(
                    f"{matched_user_skill} -> {required_skill}"
                )
        else:
            missing_skills.append(required_skill)

        skill_match_details.append({
            "required_skill": required_skill,
            "matched_user_skill": matched_user_skill,
            "match_quality": match_quality,
            "weight": skill_weight,
        })

    weighted_match_score = (
        round((matched_weight / total_possible_weight) * 100, 2)
        if total_possible_weight
        else 0.0
    )
    unweighted_match_score = round(
        (match_quality_total / len(normalized_required_skills)) * 100,
        2,
    )

    return {
        "weighted_match_score": weighted_match_score,
        "unweighted_match_score": unweighted_match_score,
        "matched_weight": round(matched_weight, 2),
        "total_possible_weight": round(total_possible_weight, 2),
        "matched_skills": matched_skills,
        "related_skills": related_skills,
        "missing_skills": missing_skills,
        "skill_match_details": skill_match_details,
    }


def get_sample_confidence(sample_size: int) -> tuple[float, str]:
    """Return a smooth sample confidence score and readable label."""
    if sample_size <= 0:
        return 0.0, "Insufficient"

    confidence_score = 1 - math.exp(-sample_size / CONFIDENCE_SAMPLE_SCALE)

    if confidence_score < MIN_HEADLINE_CONFIDENCE:
        confidence_label = "Limited"
    elif confidence_score < 0.80:
        confidence_label = "Moderate"
    else:
        confidence_label = "Strong"

    return round(confidence_score, 3), confidence_label


def select_best_role_row(role_scores_df: pd.DataFrame) -> pd.Series:
    """
    Select the best supported role row.

    Limited-sample roles remain visible in the breakdown, but they do not
    displace a role backed by a representative sample.
    """
    if role_scores_df.empty:
        return pd.Series(dtype=object)

    candidate_rows = role_scores_df

    if "headline_eligible" in role_scores_df.columns:
        eligible_rows = role_scores_df[
            role_scores_df["headline_eligible"].fillna(False)
        ]

        if not eligible_rows.empty:
            candidate_rows = eligible_rows

    sort_columns = ["weighted_match_score"]
    ascending = [False]

    if "sample_confidence_score" in candidate_rows.columns:
        sort_columns.append("sample_confidence_score")
        ascending.append(False)

    if "sample_size" in candidate_rows.columns:
        sort_columns.append("sample_size")
        ascending.append(False)

    return candidate_rows.sort_values(
        by=sort_columns,
        ascending=ascending,
    ).iloc[0]


def get_top_skills(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Count most common extracted skills across jobs."""
    all_skills = []

    for skills in df["extracted_skills"]:
        if isinstance(skills, list):
            all_skills.extend(skills)

    if not all_skills:
        return pd.DataFrame(columns=["skill", "count"])

    skill_counts = pd.Series(all_skills).value_counts().head(top_n)

    return pd.DataFrame({
        "skill": skill_counts.index,
        "count": skill_counts.values,
    })


def get_role_weighted_top_skills(
    df: pd.DataFrame,
    role_skill_weights: dict[str, dict[str, int]],
    top_n: int = 10,
) -> pd.DataFrame:
    """Rank skills by role-specific weighted importance."""
    rows = []

    for role_category, group in df.groupby("role_category"):
        skill_counts = {}

        for skills in group["extracted_skills"]:
            if not isinstance(skills, list):
                continue

            for skill in skills:
                normalized_skill = normalize_skill(skill)
                skill_counts[normalized_skill] = skill_counts.get(normalized_skill, 0) + 1

        for skill, count in skill_counts.items():
            weight = get_skill_weight_for_role(
                skill,
                role_category,
                role_skill_weights,
            )

            rows.append({
                "role_category": role_category,
                "skill": skill,
                "count": count,
                "role_weight": weight,
                "weighted_importance": count * weight,
            })

    if not rows:
        return pd.DataFrame(
            columns=[
                "role_category",
                "skill",
                "count",
                "role_weight",
                "weighted_importance",
            ]
        )

    return (
        pd.DataFrame(rows)
        .sort_values(by="weighted_importance", ascending=False)
        .head(top_n)
    )


def score_roles(df: pd.DataFrame, user_skills: list[str]) -> pd.DataFrame:
    """
    Calculate role fit from representative job-level scores.

    Each posting is scored independently. Role fit is the mean of the top
    quartile of matching postings, which avoids treating the union of every
    technology in a role category as one impossible job requirement.
    """
    if (
        df.empty
        or "role_category" not in df.columns
        or "extracted_skills" not in df.columns
    ):
        return pd.DataFrame()

    role_skill_weights = build_role_skill_weights(df)
    all_required_skills = sorted({
        normalize_skill(skill)
        for skills in df["extracted_skills"]
        if isinstance(skills, list)
        for skill in skills
        if normalize_skill(skill)
    })
    skill_match_map = build_skill_match_map(
        user_skills=user_skills,
        required_skills=all_required_skills,
    )
    role_scores = []

    for role_category, group in df.groupby("role_category"):
        job_scores = []

        for row_index, row in group.iterrows():
            raw_skills = row.get("extracted_skills", [])
            required_skills = raw_skills if isinstance(raw_skills, list) else []
            job_score = score_skill_set(
                required_skills=required_skills,
                role_category=role_category,
                role_skill_weights=role_skill_weights,
                skill_match_map=skill_match_map,
            )
            job_score["row_index"] = row_index
            job_score["title"] = str(row.get("title", ""))
            job_scores.append(job_score)

        ranked_job_scores = sorted(
            job_scores,
            key=lambda score: (
                score["weighted_match_score"],
                score["unweighted_match_score"],
            ),
            reverse=True,
        )
        representative_job_count = max(
            1,
            math.ceil(len(ranked_job_scores) * REPRESENTATIVE_JOB_QUANTILE),
        )
        representative_scores = ranked_job_scores[:representative_job_count]

        weighted_score = round(
            sum(
                score["weighted_match_score"]
                for score in representative_scores
            )
            / representative_job_count,
            2,
        )
        unweighted_score = round(
            sum(
                score["unweighted_match_score"]
                for score in representative_scores
            )
            / representative_job_count,
            2,
        )
        matched_weight = round(
            sum(score["matched_weight"] for score in representative_scores),
            2,
        )
        total_possible_weight = round(
            sum(
                score["total_possible_weight"]
                for score in representative_scores
            ),
            2,
        )

        matched_skill_scores = defaultdict(float)
        missing_skill_scores = defaultdict(float)
        related_skills = set()
        required_skills = set()

        for score in representative_scores:
            for detail in score["skill_match_details"]:
                skill = detail["required_skill"]
                match_quality = detail["match_quality"]
                skill_weight = detail["weight"]
                required_skills.add(skill)

                if match_quality >= RELATED_SKILL_THRESHOLD:
                    matched_skill_scores[skill] += skill_weight * match_quality
                else:
                    missing_skill_scores[skill] += (
                        skill_weight * (1 - match_quality)
                    )

            related_skills.update(score["related_skills"])

        matched_skills = [
            skill
            for skill, _ in sorted(
                matched_skill_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        missing_skills = [
            skill
            for skill, _ in sorted(
                missing_skill_scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]
        sample_confidence_score, sample_confidence = get_sample_confidence(
            len(group)
        )

        role_scores.append({
            "role_category": role_category,
            "sample_size": len(group),
            "weighted_match_score": weighted_score,
            "unweighted_match_score": unweighted_score,
            "matched_weight": matched_weight,
            "total_possible_weight": total_possible_weight,
            "required_skills": sorted(required_skills),
            "matched_skills": matched_skills,
            "related_skills": sorted(related_skills),
            "missing_skills": missing_skills,
            "role_skill_weights": role_skill_weights.get(role_category, {}),
            "representative_job_count": representative_job_count,
            "sample_confidence_score": sample_confidence_score,
            "sample_confidence": sample_confidence,
            "headline_eligible": (
                sample_confidence_score >= MIN_HEADLINE_CONFIDENCE
            ),
        })

    return pd.DataFrame(role_scores).sort_values(
        by=[
            "headline_eligible",
            "weighted_match_score",
            "sample_confidence_score",
        ],
        ascending=[False, False, False],
    )
