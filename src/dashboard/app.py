# src/dashboard/app.py

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_tags import st_tags

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.dashboard.charts import (
    create_learning_priority_chart,
    create_role_distribution_chart,
    create_role_match_chart,
    create_skill_importance_heatmap,
    create_top_skills_bubble_chart,
    create_weighted_vs_unweighted_chart,
)
from src.dashboard.components import (
    show_role_explanations,
    show_role_summary_cards,
)
from src.dashboard.services import (
    filter_jobs,
    get_job_match_details,
    get_learning_priorities,
    get_score_summary_metrics,
    get_tag_placeholder,
    get_top_companies,
    load_processed_jobs,
)
from src.dashboard.styles import inject_global_styles
from src.matching.match_engine import (
    build_role_skill_weights,
    get_role_weighted_top_skills,
    get_top_skills,
    score_roles,
)


st.set_page_config(
    page_title="JobLens AI",
    page_icon="🔎",
    layout="wide",
)


def main() -> None:
    inject_global_styles()

    st.title("JobLens AI")
    st.caption("Personalized job market intelligence for role fit, skill gaps, and learning priorities.")

    with st.expander("How JobLens AI calculates match scores"):
        st.write(
            """
            JobLens AI extracts skills from job postings, groups jobs into role categories,
            and calculates role-specific skill weights based on how often each skill appears
            within that category.

            The weighted match score gives more importance to skills that are more common
            within a specific role category. This avoids treating every skill equally.
            """
        )

    jobs_df = load_processed_jobs()

    with st.sidebar:
        st.header("Your Search")

        default_target_roles = [
            "Machine Learning Engineer",
            "Data Scientist",
            "AWS Cloud Engineer",
            "Backend Developer",
        ]

        target_roles = st_tags(
            label="Target Roles",
            text=get_tag_placeholder(
                session_key="target_roles_tags",
                default_tags=default_target_roles,
                placeholder="e.g. Data Scientist",
            ),
            value=default_target_roles,
            suggestions=[
                "Machine Learning Engineer",
                "Data Scientist",
                "AWS Cloud Engineer",
                "Backend Developer",
                "Data Engineer",
                "Product Analyst",
                "Software Engineer",
                "AI Engineer",
                "ML Platform Engineer",
            ],
            maxtags=10,
            key="target_roles_tags",
        )

        location = st.text_input("Location", value="Toronto ON")

        experience_level = st.selectbox(
            "Experience Level",
            options=["Any", "Entry Level", "Mid Level", "Senior"],
            index=1,
        )

        st.header("Your Skills")

        default_user_skills = [
            "Python",
            "SQL",
            "AWS",
            "Pandas",
            "Docker",
            "React",
        ]

        user_skills = st_tags(
            label="Current Skills",
            text=get_tag_placeholder(
                session_key="user_skills_tags",
                default_tags=default_user_skills,
                placeholder="e.g. Python",
            ),
            value=default_user_skills,
            suggestions=[
                "Python",
                "SQL",
                "AWS",
                "Pandas",
                "NumPy",
                "scikit-learn",
                "PyTorch",
                "TensorFlow",
                "Docker",
                "Kubernetes",
                "Spark",
                "Airflow",
                "PostgreSQL",
                "React",
                "TypeScript",
                "Tableau",
                "Power BI",
            ],
            maxtags=20,
            key="user_skills_tags",
        )

        analyze_button = st.button("Analyze Jobs", use_container_width=True)

        if st.button("Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if not analyze_button:
        st.info("Enter your target roles and skills, then click **Analyze Jobs**.")
        return

    filtered_jobs = filter_jobs(
        df=jobs_df,
        target_roles=target_roles,
        location=location,
        experience_level=experience_level,
    )

    if filtered_jobs.empty:
        st.warning("No matching jobs found. Try broadening your target roles or location.")
        return

    role_skill_weights = build_role_skill_weights(filtered_jobs)
    role_scores_df = score_roles(filtered_jobs, user_skills)

    top_skills_df = get_top_skills(filtered_jobs, top_n=10)
    weighted_top_skills_df = get_role_weighted_top_skills(
        filtered_jobs,
        role_skill_weights,
        top_n=10,
    )
    top_companies_df = get_top_companies(filtered_jobs, top_n=10)
    learning_priorities_df = get_learning_priorities(role_scores_df, filtered_jobs)
    job_match_details_df = get_job_match_details(filtered_jobs, user_skills)

    summary_metrics = get_score_summary_metrics(
        filtered_jobs=filtered_jobs,
        role_scores_df=role_scores_df,
        user_skills=user_skills,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Matching Jobs", summary_metrics["matching_jobs"])

    with col2:
        st.metric("Best Role Fit", summary_metrics["best_role"])

    with col3:
        st.metric("Average Match", f"{summary_metrics['average_match']}%")

    with col4:
        st.metric("Current Skills", summary_metrics["current_skills"])

    st.divider()

    show_role_summary_cards(role_scores_df)

    st.divider()

    show_role_explanations(role_scores_df)

    st.divider()

    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.subheader("Role Match Scores")

        score_table = role_scores_df[
            [
                "role_category",
                "sample_size",
                "weighted_match_score",
                "unweighted_match_score",
                "matched_weight",
                "total_possible_weight",
            ]
        ]

        st.dataframe(score_table, use_container_width=True)

        st.caption("Weighted score uses role-specific skill importance. Unweighted score treats all skills equally.")
        st.altair_chart(
            create_role_match_chart(role_scores_df),
            use_container_width=True,
        )

        st.subheader("Weighted vs Unweighted Comparison")
        st.caption("Shows how role-specific weighting changes the match score.")

        st.altair_chart(
            create_weighted_vs_unweighted_chart(role_scores_df),
            use_container_width=True,
        )

    with right_col:
        st.subheader("Recommended Skills to Learn")

        if learning_priorities_df.empty:
            st.success("No major missing skills found for your selected roles.")
        else:
            st.dataframe(
                learning_priorities_df.head(10),
                use_container_width=True,
            )

            st.altair_chart(
                create_learning_priority_chart(learning_priorities_df),
                use_container_width=True,
            )

    st.divider()

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Top Required Skills")
        st.caption("Most frequent skills across matching job postings.")
        st.dataframe(top_skills_df, use_container_width=True)

        if not top_skills_df.empty:
            top_skills_fig = create_top_skills_bubble_chart(top_skills_df)
            st.plotly_chart(top_skills_fig, use_container_width=True)

    with right_col:
        st.subheader("Role-Specific Skill Importance")
        st.caption("Skills ranked by role-specific frequency and importance.")
        st.dataframe(weighted_top_skills_df, use_container_width=True)

        if not weighted_top_skills_df.empty:
            st.altair_chart(
                create_skill_importance_heatmap(weighted_top_skills_df),
                use_container_width=True,
            )

    st.divider()

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Top Hiring Companies")
        st.dataframe(top_companies_df, use_container_width=True)

    with right_col:
        st.subheader("Role Distribution")
        role_counts = filtered_jobs["role_category"].value_counts()
        st.dataframe(
            role_counts.reset_index().rename(
                columns={"index": "role_category", "role_category": "job_count"}
            ),
            use_container_width=True,
        )
        st.altair_chart(
            create_role_distribution_chart(filtered_jobs),
            use_container_width=True,
        )

    st.divider()

    st.subheader("Detailed Role Breakdown")

    for _, row in role_scores_df.iterrows():
        with st.expander(
            f"{row['role_category']} — {row['weighted_match_score']}% weighted match"
        ):
            col_a, col_b = st.columns(2)

            with col_a:
                st.write("**Matched Skills**")
                if row["matched_skills"]:
                    st.write(", ".join(row["matched_skills"]))
                else:
                    st.write("No matched skills yet.")

                st.write("**Missing Skills**")
                if row["missing_skills"]:
                    st.write(", ".join(row["missing_skills"]))
                else:
                    st.write("No major missing skills.")

            with col_b:
                st.write("**Role-Specific Skill Weights**")

                weights_df = pd.DataFrame(
                    [
                        {"skill": skill, "weight": weight}
                        for skill, weight in row["role_skill_weights"].items()
                    ]
                )

                if not weights_df.empty:
                    weights_df = weights_df.sort_values(
                        by="weight",
                        ascending=False,
                    )

                st.dataframe(weights_df, use_container_width=True)

                st.write(
                    f"**Score Breakdown:** "
                    f"{row['matched_weight']} / {row['total_possible_weight']} points"
                )

    st.divider()

    st.subheader("Matching Job Postings")
    st.caption("Each posting includes a simple skill-based fit summary using your current skills.")

    st.dataframe(
        job_match_details_df[
            [
                "title",
                "company",
                "location",
                "experience_level",
                "role_category",
                "job_match_score",
                "matched_skills_count",
                "missing_skills_count",
                "matched_skills_preview",
                "missing_skills_preview",
            ]
        ],
        use_container_width=True,
    )


if __name__ == "__main__":
    main()