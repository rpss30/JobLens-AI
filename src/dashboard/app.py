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
    generate_candidate_report_markdown,
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
    read_uploaded_jobs_csv,
    load_processed_jobs,
    GREENHOUSE_AI_DEMO_PATH,
    load_processed_jobs_from_csv,
)
from src.dashboard.styles import inject_global_styles
from src.matching.match_engine import (
    build_role_skill_weights,
    get_role_weighted_top_skills,
    get_top_skills,
    score_roles,
)
from src.processing.job_processor import process_jobs
from src.database.repository import (
    build_analysis_run_name,
    check_database_connection,
    delete_dataset,
    list_analysis_runs,
    list_datasets,
    load_analysis_run,
    load_processed_jobs_dataframe,
    save_analysis_run,
    save_uploaded_dataset_from_dataframe,
)


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

@st.dialog("Confirm dataset deletion")
def confirm_delete_dataset_dialog(dataset_name: str) -> None:
    st.write(f"You are about to delete `{dataset_name}` from PostgreSQL.")
    st.warning(
        "This action cannot be undone.",
        icon=":material/warning:",
    )

    col_cancel, col_delete = st.columns(2)

    with col_cancel:
        if st.button(
            "Cancel",
            icon=":material/close:",
            use_container_width=True,
        ):
            st.rerun()

    with col_delete:
        if st.button(
            "Delete dataset",
            type="primary",
            icon=":material/delete:",
            use_container_width=True,
        ):
            try:
                deleted = delete_dataset(dataset_name)

                if deleted:
                    st.session_state.dataset_delete_success_message = (
                        f"Deleted dataset `{dataset_name}`."
                    )
                    st.rerun()

                st.session_state.dataset_delete_warning_message = (
                    f"Dataset `{dataset_name}` was not found."
                )
                st.rerun()

            except Exception as error:
                st.session_state.dataset_delete_error_message = str(error)
                st.rerun()

def main() -> None:
    inject_global_styles()

    if "analysis_requested" not in st.session_state:
        st.session_state.analysis_requested = False

    if "dataset_delete_success_message" in st.session_state:
        st.toast(
            st.session_state.dataset_delete_success_message,
            icon=":material/check_circle:",
        )
        del st.session_state.dataset_delete_success_message

    if "dataset_delete_warning_message" in st.session_state:
        st.warning(
            st.session_state.dataset_delete_warning_message,
            icon=":material/warning:",
        )
        del st.session_state.dataset_delete_warning_message

    if "dataset_delete_error_message" in st.session_state:
        st.error(
            "Could not delete selected dataset.",
            icon=":material/error:",
        )

        with st.expander("Dataset delete error details"):
            st.code(st.session_state.dataset_delete_error_message)

        del st.session_state.dataset_delete_error_message

    selected_saved_analysis_run = None

    st.title("JobLens AI")
    st.caption("Personalized job market intelligence for role fit, skill gaps, and learning priorities.")

    dataset_source = st.sidebar.selectbox(
        "Dataset source",
        options=[
            "Default sample dataset",
            "AI-extracted Greenhouse demo",
        ],
        help=(
            "Choose the local sample dataset or a generated AI-extracted "
            "Greenhouse experiment dataset if it exists."
        ),
    )

    use_database = st.sidebar.toggle(
        "Use PostgreSQL database",
        value=False,
        help="Load the curated sample jobs from PostgreSQL instead of the local processed CSV.",
    )

    uploaded_jobs_file = st.sidebar.file_uploader(
        "Upload custom jobs CSV",
        type=["csv"],
        help=(
            "CSV must include title, company, location, description, "
            "and experience_level columns."
        ),
    )

    persist_uploaded_dataset = st.sidebar.checkbox(
        "Save uploaded CSV to PostgreSQL",
        value=False,
        help=(
            "If enabled, a valid uploaded CSV will be processed and saved "
            "as a reusable PostgreSQL dataset."
        ),
    )

    selected_database_dataset = "sample_jobs"

    if use_database and check_database_connection():
        available_database_datasets = []

        try:
            available_database_datasets = list_datasets()
            dataset_names = [dataset["name"] for dataset in available_database_datasets]

            if dataset_names:
                selected_database_dataset = st.sidebar.selectbox(
                    "PostgreSQL dataset",
                    options=dataset_names,
                    index=dataset_names.index("sample_jobs")
                    if "sample_jobs" in dataset_names
                    else 0,
                    help="Choose which saved PostgreSQL dataset to analyze.",
                )
            else:
                st.sidebar.warning("No PostgreSQL datasets found.")
        except Exception as error:
            st.sidebar.warning("Could not load PostgreSQL dataset list.")

            with st.sidebar.expander("Dataset list error details"):
                st.code(str(error))

        uploaded_database_datasets = [
            dataset
            for dataset in available_database_datasets
            if dataset["source_type"] == "uploaded_csv"
        ]

        if uploaded_database_datasets:
            with st.sidebar.expander("Manage saved datasets"):
                st.caption(
                    "Only uploaded CSV datasets can be deleted. "
                    "The curated sample dataset is protected."
                )

                uploaded_dataset_names = [
                    dataset["name"] for dataset in uploaded_database_datasets
                ]

                dataset_to_delete = st.selectbox(
                    "Uploaded dataset to delete",
                    options=uploaded_dataset_names,
                    help="Choose an uploaded PostgreSQL dataset to delete.",
                )

                delete_dataset_button = st.button(
                    "Delete selected dataset",
                    type="secondary",
                    icon=":material/delete:",
                )

                if delete_dataset_button:
                    confirm_delete_dataset_dialog(dataset_to_delete)
        else:
            st.sidebar.caption("No uploaded datasets available for deletion.")

        try:
            saved_analysis_runs = list_analysis_runs()

            if saved_analysis_runs:
                saved_run_options = {
                    f"{run['name']} — {run['dataset_name']}": run["id"]
                    for run in saved_analysis_runs
                }

                selected_saved_run_label = st.sidebar.selectbox(
                    "Saved analysis preview",
                    options=["None"] + list(saved_run_options.keys()),
                    help=(
                        "Preview a previously saved analysis run. "
                        "This does not change the current live analysis filters yet."
                    ),
                )

                if selected_saved_run_label != "None":
                    selected_saved_analysis_run = load_analysis_run(
                        saved_run_options[selected_saved_run_label]
                    )
            else:
                st.sidebar.caption("No saved analysis runs yet.")
        except Exception as error:
            st.sidebar.warning("Could not load saved analysis runs.")

            with st.sidebar.expander("Saved runs error details"):
                st.code(str(error))

    if uploaded_jobs_file is not None:
        try:
            uploaded_raw_jobs_df = read_uploaded_jobs_csv(uploaded_jobs_file)
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

        if persist_uploaded_dataset:
            if use_database and check_database_connection():
                try:
                    saved_dataset_name = save_uploaded_dataset_from_dataframe(
                        df=jobs_df,
                        filename=uploaded_jobs_file.name,
                    )

                    st.sidebar.success(
                        f"Uploaded dataset saved to PostgreSQL as `{saved_dataset_name}`."
                    )
                except Exception as error:
                    st.sidebar.warning(
                        "Custom dataset loaded, but it could not be saved to PostgreSQL."
                    )

                    with st.sidebar.expander("Database save error details"):
                        st.code(str(error))
            else:
                st.sidebar.warning(
                    "Custom dataset loaded, but PostgreSQL saving was skipped because "
                    "the database toggle is off or the database is unavailable."
                )
                
        st.sidebar.success("Custom job dataset loaded.")
    else:
        if use_database:
            try:
                if check_database_connection():
                    jobs_df = load_processed_jobs_dataframe(dataset_name=selected_database_dataset)

                    if jobs_df.empty:
                        st.sidebar.warning(
                            "PostgreSQL is connected, but no jobs were found. "
                            "Using the local sample CSV instead."
                        )
                        jobs_df = load_processed_jobs()
                    else:
                        st.sidebar.success("Loaded sample jobs from PostgreSQL.")
                else:
                    st.sidebar.warning(
                        "Could not connect to PostgreSQL. "
                        "Using the local sample CSV instead."
                    )
                    jobs_df = load_processed_jobs()

            except Exception as error:
                st.sidebar.warning(
                    "PostgreSQL is unavailable. "
                    "Using the local sample CSV instead."
                )

                with st.sidebar.expander("Database error details"):
                    st.code(str(error))

                jobs_df = load_processed_jobs()
        else:
            if dataset_source == "AI-extracted Greenhouse sample":
                jobs_df = load_processed_jobs_from_csv(GREENHOUSE_AI_DEMO_PATH)

                if jobs_df.empty:
                    st.sidebar.warning(
                        "AI-extracted Greenhouse demo dataset was not found. "
                        "Using the default sample dataset instead."
                    )
                    jobs_df = load_processed_jobs()
                else:
                    st.sidebar.success("Loaded AI-extracted Greenhouse demo dataset.")
            else:
                jobs_df = load_processed_jobs()

    available_target_roles = get_available_target_roles(jobs_df)
    available_skills = get_available_skills(jobs_df)
    available_locations = get_available_locations(jobs_df)

    if selected_saved_analysis_run:
        with st.expander("Saved Analysis Preview", expanded=True):
            st.write(f"**Analysis name:** {selected_saved_analysis_run['name']}")
            st.write(f"**Dataset:** {selected_saved_analysis_run['dataset_name']}")
            st.write(f"**Best-fit role:** {selected_saved_analysis_run['best_role']}")
            st.write(
                f"**Weighted match:** "
                f"{selected_saved_analysis_run['weighted_match_score']:.1f}%"
                if selected_saved_analysis_run["weighted_match_score"] is not None
                else "**Weighted match:** N/A"
            )
            st.write(f"**Top skill gap:** {selected_saved_analysis_run['top_missing_skill']}")
            st.write(f"**Jobs analyzed:** {selected_saved_analysis_run['jobs_analyzed']}")
            st.write(
                "**Target roles:** "
                + ", ".join(selected_saved_analysis_run["target_roles"])
            )
            st.write(
                "**Current skills:** "
                + ", ".join(selected_saved_analysis_run["current_skills"])
            )

            if selected_saved_analysis_run["recommended_skills"]:
                formatted_recommended_skills = [
                    str(skill).strip().title()
                    for skill in selected_saved_analysis_run["recommended_skills"]
                    if str(skill).strip()
                ]

                st.write(
                    "**Recommended skills:** "
                    + ", ".join(formatted_recommended_skills)
                )

            saved_role_scores = selected_saved_analysis_run.get("role_scores", [])

            if saved_role_scores:
                saved_role_scores_df = pd.DataFrame(saved_role_scores)

                saved_score_columns = [
                    "role_category",
                    "sample_size",
                    "weighted_match_score",
                    "unweighted_match_score",
                    "matched_weight",
                    "total_possible_weight",
                ]

                available_saved_score_columns = [
                    column
                    for column in saved_score_columns
                    if column in saved_role_scores_df.columns
                ]

                if available_saved_score_columns:
                    st.markdown("**Saved role scores**")
                    st.dataframe(
                        saved_role_scores_df[available_saved_score_columns],
                        use_container_width=True,
                        hide_index=True,
                    )

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
        
        if analyze_button:
            st.session_state.analysis_requested = True

    if not st.session_state.analysis_requested:
        st.info("Enter your target roles and skills, then click **Analyze Jobs**.")
        return

    if not target_roles:
        st.warning(
            "Please select at least one target role before analyzing jobs."
        )
        return

    if not current_skills:
        st.warning(
            "Please select at least one current skill before analyzing jobs."
        )
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

    if use_database and check_database_connection():
        with st.expander("Save this analysis run"):
            default_analysis_name = build_analysis_run_name(
                best_role=best_role,
                dataset_name=selected_database_dataset,
            )

            analysis_name = st.text_input(
                "Analysis name",
                value=default_analysis_name,
                help="Give this analysis a readable name so you can find it later.",
            )

            save_run_button = st.button("Save analysis run")

            if save_run_button:
                try:
                    recommended_skill_names = (
                        recommended_skills_df["skill"].head(10).tolist()
                        if not recommended_skills_df.empty
                        and "skill" in recommended_skills_df.columns
                        else []
                    )

                    role_scores_to_save = role_scores_df.to_dict(orient="records")

                    saved_run_id = save_analysis_run(
                        name=analysis_name.strip() or default_analysis_name,
                        dataset_name=selected_database_dataset,
                        target_roles=target_roles,
                        location=location,
                        experience_level=experience_level,
                        current_skills=current_skills,
                        best_role=best_role,
                        weighted_match_score=float(best_score),
                        top_missing_skill=top_missing_skill,
                        jobs_analyzed=jobs_analyzed,
                        recommended_skills=recommended_skill_names,
                        role_scores=role_scores_to_save,
                    )

                    st.success(f"Analysis run saved successfully. Saved run ID: {saved_run_id}")
                except Exception as error:
                    st.error("Could not save this analysis run.")

                    with st.expander("Analysis save error details"):
                        st.code(str(error))
    else:
        st.info(
            "Turn on PostgreSQL database mode to save analysis runs."
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

    if uploaded_jobs_file is not None:
        report_dataset_name = uploaded_jobs_file.name
    elif use_database:
        report_dataset_name = selected_database_dataset
    else:
        report_dataset_name = dataset_source

    candidate_report_markdown = generate_candidate_report_markdown(
        current_skills=current_skills,
        target_roles=target_roles,
        location=location,
        experience_level=experience_level,
        filtered_jobs=filtered_jobs,
        role_scores_df=role_scores_df,
        recommended_skills_df=recommended_skills_df,
        job_match_details_df=job_match_details_df,
        candidate_fit_summary=candidate_summary,
        dataset_name=report_dataset_name,
    )

    st.download_button(
        label="Download candidate skill-gap report",
        data=candidate_report_markdown,
        file_name="joblens_candidate_skill_gap_report.md",
        mime="text/markdown",
        type="primary",
        icon=":material/download:",
    )

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