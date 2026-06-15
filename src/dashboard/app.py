# src/dashboard/app.py

import sys
import tempfile
from pathlib import Path
from typing import Any

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
    build_custom_dataset_name,
    check_database_connection,
    delete_dataset,
    list_analysis_runs,
    list_datasets,
    load_analysis_run,
    load_processed_jobs_dataframe,
    rename_dataset,
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

DATASET_SOURCE_DEFAULT = "Default sample dataset"
DATASET_SOURCE_GREENHOUSE = "AI-extracted Greenhouse demo"
DATASET_SOURCE_DATABASE = "PostgreSQL dataset"


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

def format_dataset_source_type(source_type: str) -> str:
    if source_type == "uploaded_csv":
        return "Uploaded CSV"

    if source_type == "sample_csv":
        return "Protected sample"

    return source_type.replace("_", " ").title()


def get_database_dataset_names(datasets: list[dict[str, Any]]) -> list[str]:
    return [str(dataset["name"]) for dataset in datasets]


def get_default_database_dataset(datasets: list[dict[str, Any]]) -> str:
    dataset_names = get_database_dataset_names(datasets)

    if "sample_jobs" in dataset_names:
        return "sample_jobs"

    if dataset_names:
        return dataset_names[0]

    return "sample_jobs"


def get_current_dataset_label(source: str, selected_database_dataset: str) -> str:
    if source == DATASET_SOURCE_DATABASE:
        return selected_database_dataset

    return source


def process_uploaded_jobs_file(uploaded_jobs_file) -> pd.DataFrame:
    uploaded_raw_jobs_df = read_uploaded_jobs_csv(uploaded_jobs_file)

    is_valid_upload, validation_message = validate_uploaded_jobs_csv(
        uploaded_raw_jobs_df
    )

    if not is_valid_upload:
        raise ValueError(validation_message)

    with tempfile.TemporaryDirectory(prefix="joblens_upload_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_raw_path = temp_dir_path / "uploaded_jobs.csv"
        temp_processed_path = temp_dir_path / "uploaded_processed_jobs.csv"

        uploaded_raw_jobs_df.to_csv(temp_raw_path, index=False)

        return process_jobs(
            input_path=str(temp_raw_path),
            output_path=str(temp_processed_path),
        )


@st.dialog("Choose dataset")
def choose_dataset_dialog(
    database_available: bool,
    database_datasets: list[dict[str, Any]],
) -> None:
    st.markdown("**Local datasets**")

    col_default_info, col_default_action = st.columns([4, 1])

    with col_default_info:
        st.write(DATASET_SOURCE_DEFAULT)
        st.caption("Bundled portfolio sample CSV")

    with col_default_action:
        if st.button(
            "Use",
            key="use_default_dataset",
            icon=":material/check_circle:",
            use_container_width=True,
        ):
            st.session_state.active_dataset_source = DATASET_SOURCE_DEFAULT
            st.session_state.dataset_select_success_message = (
                f"Selected `{DATASET_SOURCE_DEFAULT}`."
            )
            st.rerun()

    col_greenhouse_info, col_greenhouse_action = st.columns([4, 1])

    with col_greenhouse_info:
        st.write(DATASET_SOURCE_GREENHOUSE)
        st.caption("Generated AI-extracted demo dataset, when available")

    with col_greenhouse_action:
        if st.button(
            "Use",
            key="use_greenhouse_dataset",
            icon=":material/check_circle:",
            use_container_width=True,
        ):
            st.session_state.active_dataset_source = DATASET_SOURCE_GREENHOUSE
            st.session_state.dataset_select_success_message = (
                f"Selected `{DATASET_SOURCE_GREENHOUSE}`."
            )
            st.rerun()

    st.divider()
    st.markdown("**Saved PostgreSQL datasets**")

    if not database_available:
        st.warning(
            "PostgreSQL is unavailable, so saved datasets cannot be selected.",
            icon=":material/warning:",
        )
        return

    if not database_datasets:
        st.info("No saved PostgreSQL datasets were found.")
        return

    for dataset in database_datasets:
        dataset_name = str(dataset["name"])
        source_type = str(dataset["source_type"])
        is_active = (
            st.session_state.active_dataset_source == DATASET_SOURCE_DATABASE
            and st.session_state.selected_database_dataset == dataset_name
        )

        col_info, col_action = st.columns([4, 1])

        with col_info:
            st.write(dataset_name)
            st.caption(format_dataset_source_type(source_type))

        with col_action:
            button_label = "Active" if is_active else "Use"
            if st.button(
                button_label,
                key=f"use_database_dataset_{dataset_name}",
                icon=":material/check_circle:",
                disabled=is_active,
                use_container_width=True,
            ):
                st.session_state.active_dataset_source = DATASET_SOURCE_DATABASE
                st.session_state.selected_database_dataset = dataset_name
                st.session_state.dataset_select_success_message = (
                    f"Selected `{dataset_name}`."
                )
                st.rerun()


@st.dialog("Upload dataset")
def upload_dataset_dialog(database_available: bool) -> None:
    if not database_available:
        st.warning(
            "Turn on PostgreSQL locally before saving uploaded datasets.",
            icon=":material/warning:",
        )
        return

    uploaded_jobs_file = st.file_uploader(
        "Jobs CSV",
        type=["csv"],
        help=(
            "CSV must include title, company, location, description, "
            "and experience_level columns."
        ),
        key="dataset_upload_file",
    )

    dataset_name = st.text_input(
        "Dataset name",
        placeholder="my_custom_dataset",
        help="Required. Names are saved as lowercase, underscore-separated slugs.",
        key="dataset_upload_name",
    )

    if dataset_name.strip():
        safe_dataset_name = build_custom_dataset_name(dataset_name)
        st.caption(f"Saved name: `{safe_dataset_name}`")

    if st.button(
        "Save uploaded dataset",
        type="primary",
        icon=":material/upload_file:",
        use_container_width=True,
    ):
        if uploaded_jobs_file is None:
            st.warning(
                "Choose a jobs CSV before saving.",
                icon=":material/warning:",
            )
            return

        if not dataset_name.strip():
            st.warning(
                "Enter a dataset name before saving.",
                icon=":material/warning:",
            )
            return

        try:
            jobs_df = process_uploaded_jobs_file(uploaded_jobs_file)

            if jobs_df.empty:
                st.error(
                    "Uploaded CSV was processed, but no usable job postings were found.",
                    icon=":material/error:",
                )
                return

            saved_dataset_name = save_uploaded_dataset_from_dataframe(
                df=jobs_df,
                filename=uploaded_jobs_file.name,
                custom_name=dataset_name,
            )

            st.session_state.active_dataset_source = DATASET_SOURCE_DATABASE
            st.session_state.selected_database_dataset = saved_dataset_name
            st.session_state.dataset_upload_success_message = (
                f"Saved and selected dataset `{saved_dataset_name}`."
            )
            st.rerun()
        except pd.errors.EmptyDataError:
            st.error("Uploaded CSV is empty. Please upload a valid jobs CSV.")
        except pd.errors.ParserError:
            st.error(
                "Uploaded file could not be parsed as a valid CSV. "
                "Please check the file formatting."
            )
        except UnicodeDecodeError:
            st.error(
                "Uploaded CSV could not be decoded. Please save it as UTF-8 and try again."
            )
        except ValueError as error:
            st.error(str(error), icon=":material/error:")
        except Exception as error:
            st.error(
                "Custom dataset could not be saved to PostgreSQL.",
                icon=":material/error:",
            )

            with st.expander("Upload save error details"):
                st.code(str(error))


@st.dialog("Manage saved datasets", width="large")
def manage_saved_datasets_dialog(
    database_available: bool,
    database_datasets: list[dict[str, Any]],
) -> None:
    if not database_available:
        st.warning(
            "PostgreSQL is unavailable, so saved datasets cannot be managed.",
            icon=":material/warning:",
        )
        return

    if not database_datasets:
        st.info("No saved PostgreSQL datasets were found.")
        return

    st.caption("Uploaded CSV datasets can be renamed or deleted. Protected datasets are locked.")

    for dataset_index, dataset in enumerate(database_datasets):
        dataset_name = str(dataset["name"])
        source_type = str(dataset["source_type"])
        is_user_dataset = source_type == "uploaded_csv"

        col_info, col_actions = st.columns([5, 2])

        with col_info:
            st.write(dataset_name)
            st.caption(format_dataset_source_type(source_type))

        with col_actions:
            if st.button(
                "Rename",
                key=f"manage_edit_{dataset_name}",
                icon=":material/edit:",
                help=f"Rename {dataset_name}",
                disabled=not is_user_dataset,
                use_container_width=True,
            ):
                st.session_state.dataset_manager_action = {
                    "type": "rename",
                    "dataset_name": dataset_name,
                }

            if st.button(
                "Delete",
                key=f"manage_delete_{dataset_name}",
                icon=":material/delete:",
                help=f"Delete {dataset_name}",
                disabled=not is_user_dataset,
                use_container_width=True,
            ):
                st.session_state.dataset_manager_action = {
                    "type": "delete",
                    "dataset_name": dataset_name,
                }

        if dataset_index < len(database_datasets) - 1:
            st.divider()

    action = st.session_state.get("dataset_manager_action")

    if not action:
        return

    target_dataset_name = str(action["dataset_name"])

    st.divider()

    if action["type"] == "rename":
        st.markdown("**Rename dataset**")

        new_dataset_name = st.text_input(
            "New dataset name",
            value=target_dataset_name,
            help="Names are saved as lowercase, underscore-separated slugs.",
            key=f"rename_dataset_name_{target_dataset_name}",
        )

        if new_dataset_name.strip():
            st.caption(f"Saved name: `{build_custom_dataset_name(new_dataset_name)}`")

        col_cancel, col_save = st.columns(2)

        with col_cancel:
            if st.button(
                "Cancel",
                key=f"cancel_rename_{target_dataset_name}",
                icon=":material/close:",
                use_container_width=True,
            ):
                del st.session_state.dataset_manager_action
                st.rerun()

        with col_save:
            if st.button(
                "Save name",
                key=f"save_rename_{target_dataset_name}",
                type="primary",
                icon=":material/check_circle:",
                use_container_width=True,
            ):
                if not new_dataset_name.strip():
                    st.warning(
                        "Enter a new dataset name before saving.",
                        icon=":material/warning:",
                    )
                    return

                try:
                    renamed = rename_dataset(target_dataset_name, new_dataset_name)
                    safe_new_dataset_name = build_custom_dataset_name(new_dataset_name)

                    if renamed:
                        if st.session_state.selected_database_dataset == target_dataset_name:
                            st.session_state.selected_database_dataset = safe_new_dataset_name

                        st.session_state.dataset_rename_success_message = (
                            f"Renamed dataset `{target_dataset_name}` to `{safe_new_dataset_name}`."
                        )
                        del st.session_state.dataset_manager_action
                        st.rerun()

                    st.session_state.dataset_rename_warning_message = (
                        f"Dataset `{target_dataset_name}` was not found."
                    )
                    del st.session_state.dataset_manager_action
                    st.rerun()
                except Exception as error:
                    st.session_state.dataset_rename_error_message = str(error)
                    del st.session_state.dataset_manager_action
                    st.rerun()

    if action["type"] == "delete":
        st.markdown("**Delete dataset**")
        st.warning(
            f"You are about to delete `{target_dataset_name}`. This action cannot be undone.",
            icon=":material/warning:",
        )

        col_cancel, col_delete = st.columns(2)

        with col_cancel:
            if st.button(
                "Cancel",
                key=f"cancel_delete_{target_dataset_name}",
                icon=":material/close:",
                use_container_width=True,
            ):
                del st.session_state.dataset_manager_action
                st.rerun()

        with col_delete:
            if st.button(
                "Delete dataset",
                key=f"confirm_delete_{target_dataset_name}",
                type="primary",
                icon=":material/delete:",
                use_container_width=True,
            ):
                try:
                    deleted = delete_dataset(target_dataset_name)

                    if deleted:
                        if st.session_state.selected_database_dataset == target_dataset_name:
                            st.session_state.selected_database_dataset = "sample_jobs"

                        st.session_state.dataset_delete_success_message = (
                            f"Deleted dataset `{target_dataset_name}`."
                        )
                        del st.session_state.dataset_manager_action
                        st.rerun()

                    st.session_state.dataset_delete_warning_message = (
                        f"Dataset `{target_dataset_name}` was not found."
                    )
                    del st.session_state.dataset_manager_action
                    st.rerun()
                except Exception as error:
                    st.session_state.dataset_delete_error_message = str(error)
                    del st.session_state.dataset_manager_action
                    st.rerun()

def main() -> None:
    inject_global_styles()

    if "analysis_requested" not in st.session_state:
        st.session_state.analysis_requested = False

    if "active_dataset_source" not in st.session_state:
        st.session_state.active_dataset_source = DATASET_SOURCE_DEFAULT

    if "selected_database_dataset" not in st.session_state:
        st.session_state.selected_database_dataset = "sample_jobs"

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

    if "dataset_rename_success_message" in st.session_state:
        st.toast(
            st.session_state.dataset_rename_success_message,
            icon=":material/check_circle:",
        )
        del st.session_state.dataset_rename_success_message

    if "dataset_rename_warning_message" in st.session_state:
        st.warning(
            st.session_state.dataset_rename_warning_message,
            icon=":material/warning:",
        )
        del st.session_state.dataset_rename_warning_message

    if "dataset_rename_error_message" in st.session_state:
        st.error(
            "Could not rename selected dataset.",
            icon=":material/error:",
        )

        with st.expander("Dataset rename error details"):
            st.code(st.session_state.dataset_rename_error_message)

        del st.session_state.dataset_rename_error_message

    if "dataset_upload_success_message" in st.session_state:
        st.toast(
            st.session_state.dataset_upload_success_message,
            icon=":material/check_circle:",
        )
        del st.session_state.dataset_upload_success_message

    if "dataset_select_success_message" in st.session_state:
        st.toast(
            st.session_state.dataset_select_success_message,
            icon=":material/check_circle:",
        )
        del st.session_state.dataset_select_success_message

    selected_saved_analysis_run = None

    st.title("JobLens AI")
    st.caption("Personalized job market intelligence for role fit, skill gaps, and learning priorities.")

    database_available = check_database_connection()
    available_database_datasets: list[dict[str, Any]] = []
    database_list_error: Exception | None = None

    if database_available:
        try:
            available_database_datasets = list_datasets()
        except Exception as error:
            database_list_error = error

    database_dataset_names = get_database_dataset_names(available_database_datasets)

    if (
        st.session_state.active_dataset_source == DATASET_SOURCE_DATABASE
        and database_dataset_names
        and st.session_state.selected_database_dataset not in database_dataset_names
    ):
        st.session_state.selected_database_dataset = get_default_database_dataset(
            available_database_datasets
        )

    selected_database_dataset = st.session_state.selected_database_dataset
    dataset_source = st.session_state.active_dataset_source
    use_database = dataset_source == DATASET_SOURCE_DATABASE

    with st.sidebar:
        dataset_heading_col, dataset_help_col = st.columns(
            [0.82, 0.18],
            vertical_alignment="center",
        )

        with dataset_heading_col:
            st.header("Dataset")

        with dataset_help_col:
            st.markdown(
                '<span class="dataset-info-popover-anchor"></span>',
                unsafe_allow_html=True,
            )
            with st.popover(
                "Dataset info",
                icon=":material/help:",
                help="Dataset info",
                width="content",
            ):
                st.markdown("**Expected dataset**")
                st.write(
                    "Use a jobs CSV with `title`, `company`, `location`, "
                    "`description`, and `experience_level` columns."
                )
                st.write(
                    "The selected dataset is the job market sample used for "
                    "role-fit scoring, skill gaps, recommendations, and charts."
                )
                st.write(
                    "Uploaded PostgreSQL datasets are reusable. Protected sample "
                    "datasets cannot be renamed or deleted."
                )

        st.caption("Current dataset")
        st.write(f"**{get_current_dataset_label(dataset_source, selected_database_dataset)}**")

        if use_database:
            st.markdown(
                '<span class="postgres-toggle-marker postgres-toggle-on"></span>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Turn off PostgreSQL",
                icon=":material/database_off:",
                use_container_width=True,
            ):
                st.session_state.active_dataset_source = DATASET_SOURCE_DEFAULT
                st.session_state.dataset_select_success_message = (
                    f"Selected `{DATASET_SOURCE_DEFAULT}`."
                )
                st.rerun()
        else:
            st.markdown(
                '<span class="postgres-toggle-marker postgres-toggle-off"></span>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Turn on PostgreSQL",
                icon=":material/database:",
                use_container_width=True,
            ):
                if not database_available:
                    st.warning(
                        "PostgreSQL is unavailable right now.",
                        icon=":material/warning:",
                    )
                elif not available_database_datasets:
                    st.warning(
                        "No PostgreSQL datasets were found.",
                        icon=":material/warning:",
                    )
                else:
                    selected_default_database_dataset = get_default_database_dataset(
                        available_database_datasets
                    )
                    st.session_state.active_dataset_source = DATASET_SOURCE_DATABASE
                    st.session_state.selected_database_dataset = (
                        selected_default_database_dataset
                    )
                    st.session_state.dataset_select_success_message = (
                        f"Selected `{selected_default_database_dataset}`."
                    )
                    st.rerun()

        if database_list_error is not None:
            st.warning("Could not load PostgreSQL dataset list.")

            with st.expander("Dataset list error details"):
                st.code(str(database_list_error))

        if st.button(
            "Choose dataset",
            icon=":material/database:",
            use_container_width=True,
        ):
            choose_dataset_dialog(
                database_available=database_available,
                database_datasets=available_database_datasets,
            )

        if st.button(
            "Upload dataset",
            icon=":material/upload_file:",
            use_container_width=True,
        ):
            upload_dataset_dialog(database_available=database_available)

        if st.button(
            "Manage saved datasets",
            icon=":material/settings:",
            use_container_width=True,
        ):
            manage_saved_datasets_dialog(
                database_available=database_available,
                database_datasets=available_database_datasets,
            )

        if use_database and database_available:
            try:
                saved_analysis_runs = list_analysis_runs()

                if saved_analysis_runs:
                    saved_run_options = {
                        f"{run['name']} — {run['dataset_name']}": run["id"]
                        for run in saved_analysis_runs
                    }

                    selected_saved_run_label = st.selectbox(
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
                    st.caption("No saved analysis runs yet.")
            except Exception as error:
                st.warning("Could not load saved analysis runs.")

                with st.expander("Saved runs error details"):
                    st.code(str(error))

    if use_database:
        try:
            if database_available:
                jobs_df = load_processed_jobs_dataframe(
                    dataset_name=selected_database_dataset
                )

                if jobs_df.empty:
                    st.sidebar.warning(
                        "PostgreSQL is connected, but no jobs were found. "
                        "Using the local sample CSV instead."
                    )
                    jobs_df = load_processed_jobs()
                else:
                    st.sidebar.success(
                        f"Loaded `{selected_database_dataset}` from PostgreSQL."
                    )
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
        if dataset_source == DATASET_SOURCE_GREENHOUSE:
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

    if use_database:
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
