# src/dashboard/app.py

import pandas as pd
import streamlit as st

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.processing.job_processor import process_jobs
from src.matching.match_engine import get_top_skills, score_roles


RAW_DATA_PATH = "data/raw/sample_jobs.csv"
PROCESSED_DATA_PATH = "data/processed/processed_jobs.csv"


st.set_page_config(
    page_title="JobLens AI",
    page_icon="🔎",
    layout="wide",
)


@st.cache_data
def load_processed_jobs() -> pd.DataFrame:
    """Load and process job data once for the dashboard."""
    return process_jobs(
        input_path=RAW_DATA_PATH,
        output_path=PROCESSED_DATA_PATH,
    )


def filter_jobs(
    df: pd.DataFrame,
    target_roles: list[str],
    location: str,
    experience_level: str,
) -> pd.DataFrame:
    """Filter jobs based on user input."""
    filtered_df = df.copy()

    if target_roles:
        role_keywords = [role.strip().lower() for role in target_roles if role.strip()]

        if role_keywords:
            filtered_df = filtered_df[
                filtered_df["clean_title"].apply(
                    lambda title: any(keyword in title for keyword in role_keywords)
                )
            ]

    if location:
        location_lower = location.strip().lower()
        filtered_df = filtered_df[
            filtered_df["location"].str.lower().str.contains(location_lower, na=False)
        ]

    if experience_level and experience_level != "Any":
        filtered_df = filtered_df[
            filtered_df["experience_level"].str.lower()
            == experience_level.lower()
        ]

    return filtered_df


def get_top_companies(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return companies with the most matching job postings."""
    company_counts = df["company"].value_counts().head(top_n)

    return pd.DataFrame({
        "company": company_counts.index,
        "job_count": company_counts.values,
    })


def get_missing_skills_summary(role_scores_df: pd.DataFrame) -> pd.DataFrame:
    """Count missing skills across all matched role categories."""
    missing_skills = []

    for skills in role_scores_df["missing_skills"]:
        if isinstance(skills, list):
            missing_skills.extend(skills)

    if not missing_skills:
        return pd.DataFrame(columns=["skill", "count"])

    counts = pd.Series(missing_skills).value_counts()

    return pd.DataFrame({
        "skill": counts.index,
        "count": counts.values,
    })


def main() -> None:
    st.title("🔎 JobLens AI")
    st.subheader("Personalized Job Market Intelligence Platform")

    st.write(
        "Enter your target roles, location, and current skills to see role match scores, "
        "in-demand skills, hiring companies, and skill gaps."
    )

    jobs_df = load_processed_jobs()

    with st.sidebar:
        st.header("Your Profile")

        target_roles_input = st.text_area(
            "Target Roles",
            value="Machine Learning Engineer\nData Scientist\nAWS Cloud Engineer",
            help="Enter one role per line.",
        )

        location = st.text_input(
            "Location",
            value="Toronto ON",
        )

        current_skills_input = st.text_area(
            "Current Skills",
            value="Python\nSQL\nAWS\nReact\nPandas",
            help="Enter one skill per line.",
        )

        experience_level = st.selectbox(
            "Experience Level",
            options=["Any", "Entry Level", "Mid Level", "Senior"],
            index=1,
        )

        analyze_button = st.button("Analyze Jobs")

    target_roles = [
        role.strip()
        for role in target_roles_input.splitlines()
        if role.strip()
    ]

    user_skills = [
        skill.strip()
        for skill in current_skills_input.splitlines()
        if skill.strip()
    ]

    if analyze_button:
        filtered_jobs = filter_jobs(
            df=jobs_df,
            target_roles=target_roles,
            location=location,
            experience_level=experience_level,
        )

        if filtered_jobs.empty:
            st.warning("No matching jobs found. Try broadening your target roles or location.")
            return

        role_scores_df = score_roles(filtered_jobs, user_skills)
        top_skills_df = get_top_skills(filtered_jobs, top_n=10)
        top_companies_df = get_top_companies(filtered_jobs, top_n=10)
        missing_skills_df = get_missing_skills_summary(role_scores_df)

        total_jobs = len(filtered_jobs)
        avg_match_score = round(role_scores_df["match_score"].mean(), 2)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Matching Jobs", total_jobs)

        with col2:
            st.metric("Average Role Match", f"{avg_match_score}%")

        with col3:
            st.metric("Unique Role Categories", filtered_jobs["role_category"].nunique())

        st.divider()

        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("Role Match Scores")
            st.dataframe(
                role_scores_df[["role_category", "match_score"]],
                use_container_width=True,
            )

            st.bar_chart(
                role_scores_df.set_index("role_category")["match_score"]
            )

        with right_col:
            st.subheader("Top Required Skills")
            st.dataframe(top_skills_df, use_container_width=True)

            if not top_skills_df.empty:
                st.bar_chart(
                    top_skills_df.set_index("skill")["count"]
                )

        st.divider()

        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("Missing Skills")
            if missing_skills_df.empty:
                st.success("You already match the required skills well.")
            else:
                st.dataframe(
                    missing_skills_df.head(10),
                    use_container_width=True,
                )

        with right_col:
            st.subheader("Top Hiring Companies")
            st.dataframe(
                top_companies_df,
                use_container_width=True,
            )

        st.divider()

        st.subheader("Matching Job Postings")
        st.dataframe(
            filtered_jobs[
                [
                    "title",
                    "company",
                    "location",
                    "role_category",
                    "skills_text",
                ]
            ],
            use_container_width=True,
        )

        st.divider()

        st.subheader("Detailed Role Skill Gaps")

        for _, row in role_scores_df.iterrows():
            with st.expander(f"{row['role_category']} — {row['match_score']}% match"):
                st.write("**Required Skills:**")
                st.write(", ".join(row["required_skills"]))

                st.write("**Missing Skills:**")
                if row["missing_skills"]:
                    st.write(", ".join(row["missing_skills"]))
                else:
                    st.write("No major missing skills.")


if __name__ == "__main__":
    main()