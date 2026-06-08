# src/dashboard/app.py

import sys
from pathlib import Path
import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from src.dashboard.charts import (
    # create_learning_priority_chart,
    create_jobs_by_location_chart,
    create_recommended_skills_chart,
    create_role_distribution_chart,
    create_role_match_chart,
    create_skill_importance_heatmap,
    create_top_skills_bubble_chart,
    create_weighted_vs_unweighted_chart,
)
from src.dashboard.components import (
    show_candidate_fit_summary,
    show_role_explanations,
    show_role_summary_cards,
    show_top_job_match_cards,
)
from src.dashboard.services import (
    filter_jobs,
    get_available_locations,
    get_available_skills,
    get_available_target_roles,
    get_candidate_fit_summary,
    get_job_match_details,
    get_jobs_by_location,
    get_recommended_skills,
    get_role_sample_context,
    get_top_companies,
    validate_uploaded_jobs_csv,
    load_processed_jobs,
)
from src.dashboard.styles import inject_global_styles

from src.matching.match_engine import (
    build_role_skill_weights,
    get_role_weighted_top_skills,
    get_top_skills,
    score_roles,
)

from src.processing.job_processor import process_jobs


st.set_page_config(
    page_title="JobLens AI",
    page_icon="🔎",
    layout="wide",
)

PRESET_PROFILES = {
    "Custom": [],
    "Aspiring Data Scientist": [
        "Python",
        "SQL",
        "Pandas",
        "NumPy",
        "scikit-learn",
        "statistics",
        "data visualization",
    ],
    "Aspiring ML Engineer": [
        "Python",
        "PyTorch",
        "TensorFlow",
        "scikit-learn",
        "Docker",
        "AWS",
        "model deployment",
    ],
    "Aspiring Cloud / AWS Engineer": [
        "AWS",
        "EC2",
        "S3",
        "Lambda",
        "Docker",
        "Terraform",
        "Kubernetes",
    ],
    "Backend Developer": [
        "Python",
        "REST APIs",
        "PostgreSQL",
        "Docker",
        "AWS",
    ],
    "Analytics Candidate": [
        "SQL",
        "Tableau",
        "Power BI",
        "statistics",
        "data visualization",
        "A/B testing",
    ],
}

SEARCH_PRESETS = {
    "Custom": {
        "target_roles": ["Machine Learning Engineer"],
        "location": "Any",
        "experience_level": "Entry Level",
    },
    "AI / ML Roles": {
        "target_roles": [
            "Machine Learning Engineer",
            "AI Engineer",
            "ML Platform Engineer",
        ],
        "location": "Any",
        "experience_level": "Entry Level",
    },
    "Data Science Roles": {
        "target_roles": [
            "Data Scientist",
            "Junior Data Scientist",
        ],
        "location": "Any",
        "experience_level": "Entry Level",
    },
    "Cloud / AWS Roles": {
        "target_roles": [
            "AWS Cloud Engineer",
            "Cloud Engineer",
            "Junior DevOps Engineer",
            "Platform Engineer",
        ],
        "location": "Any",
        "experience_level": "Entry Level",
    },
    "Software Engineering Roles": {
        "target_roles": [
            "Backend Developer",
            "Backend Engineer",
            "Software Engineer",
            "Full Stack Developer",
        ],
        "location": "Any",
        "experience_level": "Entry Level",
    },
    "Analytics Roles": {
        "target_roles": [
            "Data Analyst",
            "Product Analyst",
            "Business Intelligence Analyst",
            "Business Analyst",
        ],
        "location": "Any",
        "experience_level": "Entry Level",
    },
    "Data Engineering Roles": {
        "target_roles": [
            "Data Engineer",
            "Junior Data Engineer",
            "Cloud Data Engineer",
            "Analytics Engineer",
        ],
        "location": "Any",
        "experience_level": "Entry Level",
    },
}

def get_top_insights(
    role_scores_df: pd.DataFrame,
    recommended_skills_df: pd.DataFrame,
    filtered_jobs_df: pd.DataFrame,
) -> tuple[str, float, str, int]:
    """
    Returns dashboard-level summary insights.
    """

    if role_scores_df.empty:
        return "No match", 0.0, "No skill gap", 0

    best_role_row = role_scores_df.sort_values(
        by="weighted_match_score",
        ascending=False,
    ).iloc[0]

    best_role = best_role_row["role_category"]
    best_score = best_role_row["weighted_match_score"]

    if recommended_skills_df.empty:
        top_missing_skill = "No major gaps"
    else:
        top_missing_skill = recommended_skills_df.iloc[0]["skill"]

    jobs_analyzed = len(filtered_jobs_df)

    return best_role, best_score, top_missing_skill, jobs_analyzed

def main() -> None:
    inject_global_styles()

    st.title("JobLens AI")
    st.caption("Personalized job market intelligence for role fit, skill gaps, and learning priorities.")

    uploaded_jobs_file = st.sidebar.file_uploader(
        "Upload custom jobs CSV",
        type=["csv"],
        help=(
            "CSV must include title, company, location, description, "
            "and experience_level columns."
        ),
    )

    if uploaded_jobs_file is not None:
        try:
            uploaded_raw_jobs_df = pd.read_csv(
                uploaded_jobs_file,
                engine="python",
                on_bad_lines="error",
            )
        except pd.errors.EmptyDataError:
            st.error("Uploaded CSV is empty. Please upload a valid jobs CSV.")
            return
        except pd.errors.ParserError:
            st.error(
                "Uploaded file could not be parsed as a valid CSV. "
                "Please check the file formatting."
            )
            return
        except UnicodeDecodeError:
            st.error(
                "Uploaded CSV could not be decoded. Please save it as UTF-8 and try again."
            )
            return

        is_valid_upload, validation_message = validate_uploaded_jobs_csv(
            uploaded_raw_jobs_df
        )

        if not is_valid_upload:
            st.error(validation_message)
            return

        temp_raw_path = "data/raw/uploaded_jobs.csv"
        temp_processed_path = "data/processed/uploaded_processed_jobs.csv"

        uploaded_raw_jobs_df.to_csv(temp_raw_path, index=False)

        jobs_df = process_jobs(
            input_path=temp_raw_path,
            output_path=temp_processed_path,
        )

        if jobs_df.empty:
            st.error(
                "Uploaded CSV was processed, but no usable job postings were found."
            )
            return

        if "extracted_skills" in jobs_df.columns:
            has_extracted_skills = jobs_df["extracted_skills"].apply(
                lambda skills: bool(skills)
                if isinstance(skills, list)
                else bool(str(skills).strip())
            ).any()

            if not has_extracted_skills:
                st.warning(
                    "Custom dataset loaded, but no known skills were extracted. "
                    "Try using descriptions with skills such as Python, SQL, AWS, Docker, Pandas, or PyTorch."
                )

        st.sidebar.success("Custom job dataset loaded.")
    else:
        jobs_df = load_processed_jobs()

    available_target_roles = get_available_target_roles(jobs_df)
    available_skills = get_available_skills(jobs_df)
    available_locations = get_available_locations(jobs_df)

    # with st.expander("Debug: dataset preview"):
    #     st.write("Total jobs loaded:", len(jobs_df))
    #     st.write("Columns:", list(jobs_df.columns))

    #     if "title" in jobs_df.columns:
    #         st.write("Sample titles:", jobs_df["title"].head(10).tolist())

    #     if "clean_title" in jobs_df.columns:
    #         st.write("Sample clean titles:", jobs_df["clean_title"].head(10).tolist())

    #     if "location" in jobs_df.columns:
    #         st.write("Unique locations:", jobs_df["location"].dropna().unique().tolist())

    #     if "experience_level" in jobs_df.columns:
    #         st.write(
    #             "Unique experience levels:",
    #             jobs_df["experience_level"].dropna().unique().tolist(),
    #         )

    with st.sidebar:
        st.header("Your Job Search")

        search_preset = st.selectbox(
            "Try a sample search",
            list(SEARCH_PRESETS.keys()),
        )

        selected_search = SEARCH_PRESETS[search_preset]

        target_role_options = sorted(
            set(available_target_roles).union(selected_search["target_roles"])
        )

        target_roles = st.multiselect(
            "Target roles",
            options=target_role_options,
            default=selected_search["target_roles"],
        )

        location_options = sorted(
            set(available_locations).union({selected_search["location"]})
        )

        location_options = [
            location for location in location_options
            if location != "Any"
        ]

        location_options = ["Any"] + location_options

        default_location_index = (
            location_options.index(selected_search["location"])
            if selected_search["location"] in location_options
            else 0
        )

        location = st.selectbox(
            "Location",
            location_options,
            index=default_location_index,
        )

        experience_level_options = ["Any", "Entry Level", "Mid Level", "Senior Level"]

        default_experience_index = (
            experience_level_options.index(selected_search["experience_level"])
            if selected_search["experience_level"] in experience_level_options
            else 0
        )

        experience_level = st.selectbox(
            "Experience level",
            experience_level_options,
            index=default_experience_index,
        )

        profile_preset = st.selectbox(
            "Try a sample profile",
            list(PRESET_PROFILES.keys()),
        )

        default_skills = (
            PRESET_PROFILES[profile_preset]
            if profile_preset != "Custom"
            else ["Python", "SQL", "Pandas"]
        )

        skill_options = sorted(
            set(available_skills).union(default_skills)
        )

        current_skills = st.multiselect(
            "Current skills",
            options=skill_options,
            default=default_skills,
        )

        analyze_button = st.button("Analyze Jobs", type="primary")

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
        st.warning(
            "No matching jobs found. Try selecting a broader sample search, removing some target roles, or clearing the location filter."
        )
        return
    role_skill_weights = build_role_skill_weights(filtered_jobs)

    role_scores_df = score_roles(
        filtered_jobs,
        current_skills,
    )

    recommended_skills_df = get_recommended_skills(
        jobs_df=filtered_jobs,
        user_skills=current_skills,
        role_skill_weights=role_skill_weights,
        top_n=10,
    )

    candidate_summary = get_candidate_fit_summary(
        filtered_jobs=filtered_jobs,
        role_scores_df=role_scores_df,
        recommended_skills_df=recommended_skills_df,
    )

    best_role, best_score, top_missing_skill, jobs_analyzed = get_top_insights(
        role_scores_df=role_scores_df,
        recommended_skills_df=recommended_skills_df,
        filtered_jobs_df=filtered_jobs,
    )

    role_sample_context_df = get_role_sample_context(filtered_jobs)

    st.subheader("Role Fit Overview")

    col1, col2, col3, col4, col5 = st.columns([1.35, 1.1, 1.1, 0.9, 0.9])

    with col1:
        st.metric("Best-fit role", best_role)

    with col2:
        st.metric("Weighted match", f"{best_score:.1f}%")

    with col3:
        st.metric("Top skill gap", top_missing_skill)

    with col4:
        st.metric("Jobs analyzed", jobs_analyzed)

    with col5:
        st.metric("Current skills", len(current_skills))
    
    st.caption(
        "Weighted match prioritizes skills that appear more often within each role category."
    )

    show_candidate_fit_summary(candidate_summary)

    top_skills_df = get_top_skills(filtered_jobs, top_n=10)
    weighted_top_skills_df = get_role_weighted_top_skills(
        filtered_jobs,
        role_skill_weights,
        top_n=10,
    )
    top_companies_df = get_top_companies(filtered_jobs, top_n=10)
    jobs_by_location_df = get_jobs_by_location(filtered_jobs)
    job_match_details_df = get_job_match_details(filtered_jobs, current_skills)

    st.divider()

    show_role_summary_cards(role_scores_df)

    st.divider()

    show_role_explanations(role_scores_df)

    with st.expander("Role sample size context"):
        st.caption(
            "Shows how many postings were analyzed per role category. Larger samples make role-specific skill weights more reliable."
        )
        st.dataframe(
            role_sample_context_df,
            use_container_width=True,
            hide_index=True,
        )

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

        if recommended_skills_df.empty:
            st.success("No major missing skills found for your selected roles.")
        else:
            st.dataframe(
                recommended_skills_df.head(10),
                use_container_width=True,
                hide_index=True,
            )

            recommended_skills_chart = create_recommended_skills_chart(
                recommended_skills_df
            )

            if recommended_skills_chart is not None:
                st.altair_chart(
                    recommended_skills_chart,
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
        st.caption("Companies with the most postings in your filtered search.")
        st.dataframe(
            top_companies_df,
            use_container_width=True,
            hide_index=True,
        )

    with right_col:
        st.subheader("Jobs by Location")
        st.caption("Where matching postings are concentrated across your selected filters.")

        st.dataframe(
            jobs_by_location_df,
            use_container_width=True,
            hide_index=True,
        )

        location_chart = create_jobs_by_location_chart(jobs_by_location_df)

        if location_chart is not None:
            st.altair_chart(
                location_chart,
                use_container_width=True,
            )

    st.divider()

    st.subheader("Role Distribution")
    st.caption("Breakdown of matching postings by role category.")

    role_counts = filtered_jobs["role_category"].value_counts()
    role_distribution_df = role_counts.reset_index()
    role_distribution_df.columns = ["role_category", "job_count"]

    st.dataframe(
        role_distribution_df,
        use_container_width=True,
        hide_index=True,
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

    show_top_job_match_cards(
        job_match_details_df=job_match_details_df,
        top_n=5,
    )

    with st.expander("View all matching jobs as a table"):
        job_display_columns = [
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

        available_job_columns = [
            column for column in job_display_columns
            if column in job_match_details_df.columns
        ]

        st.dataframe(
            job_match_details_df[available_job_columns],
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()