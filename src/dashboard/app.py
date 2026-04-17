# src/dashboard/app.py

import sys
from pathlib import Path
from streamlit_tags import st_tags

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go

from src.processing.job_processor import process_jobs
from src.matching.match_engine import (
    build_role_skill_weights,
    get_role_weighted_top_skills,
    get_top_skills,
    score_roles,
)


RAW_DATA_PATH = "data/raw/sample_jobs.csv"
PROCESSED_DATA_PATH = "data/processed/processed_jobs.csv"


st.set_page_config(
    page_title="JobLens AI",
    page_icon="🔎",
    layout="wide",
)


@st.cache_data
def load_processed_jobs() -> pd.DataFrame:
    """Load and process job data once."""
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
        role_keywords = [
            role.strip().lower()
            for role in target_roles
            if role.strip()
        ]

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
    """Return companies with the most matching jobs."""
    company_counts = df["company"].value_counts().head(top_n)

    return pd.DataFrame({
        "company": company_counts.index,
        "job_count": company_counts.values,
    })


def get_learning_priorities(role_scores_df: pd.DataFrame) -> pd.DataFrame:
    """
    Rank missing skills by importance across role categories.

    priority_score = role-specific weight summed across all roles where missing
    """
    rows = []

    for _, row in role_scores_df.iterrows():
        role_category = row["role_category"]
        role_weights = row["role_skill_weights"]

        for skill in row["missing_skills"]:
            weight = role_weights.get(skill, 1)

            rows.append({
                "skill": skill,
                "role_category": role_category,
                "weight": weight,
                "priority_score": weight,
            })

    if not rows:
        return pd.DataFrame(
            columns=["skill", "roles_missing_for", "total_priority_score"]
        )

    priorities_df = pd.DataFrame(rows)

    grouped_df = (
        priorities_df
        .groupby("skill")
        .agg(
            roles_missing_for=("role_category", lambda roles: ", ".join(sorted(set(roles)))),
            total_priority_score=("priority_score", "sum"),
        )
        .reset_index()
        .sort_values(by="total_priority_score", ascending=False)
    )

    return grouped_df


def show_role_summary_cards(role_scores_df: pd.DataFrame) -> None:
    """Show top role matches as metric cards."""
    st.subheader("Best Role Matches")

    top_roles = role_scores_df.head(3)

    cols = st.columns(3)

    for col, (_, row) in zip(cols, top_roles.iterrows()):
        with col:
            st.metric(
                label=row["role_category"],
                value=f"{row['weighted_match_score']}%",
                delta=f"{row['matched_weight']} / {row['total_possible_weight']} pts",
            )

def create_role_match_chart(role_scores_df: pd.DataFrame):
    """Create horizontal bar chart for weighted role match scores."""
    chart_df = role_scores_df.sort_values(
        by="weighted_match_score",
        ascending=True,
    )

    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("weighted_match_score:Q", title="Weighted Match Score (%)"),
            y=alt.Y("role_category:N", sort=None, title="Role Category"),
            tooltip=[
                "role_category",
                "sample_size",
                "weighted_match_score",
                "unweighted_match_score",
                "matched_weight",
                "total_possible_weight",
            ],
        )
        .properties(height=280)
    )


def create_weighted_vs_unweighted_chart(role_scores_df: pd.DataFrame):
    """Compare weighted and unweighted match scores."""
    chart_df = role_scores_df[
        ["role_category", "weighted_match_score", "unweighted_match_score"]
    ].melt(
        id_vars="role_category",
        var_name="score_type",
        value_name="score",
    )

    chart_df["score_type"] = chart_df["score_type"].replace({
        "weighted_match_score": "Weighted",
        "unweighted_match_score": "Unweighted",
    })

    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("score:Q", title="Score (%)"),
            y=alt.Y("role_category:N", title="Role Category"),
            color=alt.Color("score_type:N", title="Score Type"),
            tooltip=["role_category", "score_type", "score"],
        )
        .properties(height=300)
    )


def create_learning_priority_chart(learning_priorities_df: pd.DataFrame):
    """Create horizontal chart for recommended learning priorities."""
    chart_df = learning_priorities_df.head(10).sort_values(
        by="total_priority_score",
        ascending=True,
    )

    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("total_priority_score:Q", title="Priority Score"),
            y=alt.Y("skill:N", sort=None, title="Skill"),
            tooltip=["skill", "roles_missing_for", "total_priority_score"],
        )
        .properties(height=320)
    )


def create_skill_importance_heatmap(weighted_top_skills_df: pd.DataFrame):
    """Create heatmap for role-specific skill importance."""
    return (
        alt.Chart(weighted_top_skills_df)
        .mark_rect()
        .encode(
            x=alt.X("skill:N", title="Skill"),
            y=alt.Y("role_category:N", title="Role Category"),
            color=alt.Color("role_weight:Q", title="Role Weight"),
            tooltip=[
                "role_category",
                "skill",
                "count",
                "role_weight",
                "weighted_importance",
            ],
        )
        .properties(height=260)
    )


def create_top_skills_bubble_chart(top_skills_df: pd.DataFrame):
    """Create a packed-style bubble chart for top required skills."""
    if top_skills_df.empty:
        return None

    chart_df = top_skills_df.head(10).copy()
    chart_df = chart_df.sort_values(by="count", ascending=False).reset_index(drop=True)

    positions = [
        (0.0, 0.0),
        (1.45, 0.15),
        (-1.35, 0.2),
        (0.1, 1.25),
        (-0.35, -1.2),
        (1.45, -1.0),
        (-1.55, -1.0),
        (0.95, 1.35),
        (-0.95, 1.35),
        (0.0, -1.9),
    ]

    chart_df["x"] = [positions[i][0] for i in range(len(chart_df))]
    chart_df["y"] = [positions[i][1] for i in range(len(chart_df))]

    max_count = chart_df["count"].max()
    chart_df["bubble_size"] = chart_df["count"].apply(
        lambda count: 45 + (count / max_count) * 105
    )

    chart_df["label"] = chart_df.apply(
        lambda row: f"<b>{row['skill']}</b><br>{row['count']} jobs",
        axis=1,
    )

    bubble_colors = [
        "#2563EB",
        "#16A34A",
        "#F97316",
        "#9333EA",
        "#DC2626",
        "#0891B2",
        "#CA8A04",
        "#4F46E5",
        "#DB2777",
        "#059669",
    ]

    chart_df["color"] = [
        bubble_colors[i % len(bubble_colors)]
        for i in range(len(chart_df))
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_df["x"],
            y=chart_df["y"],
            mode="markers+text",
            marker=dict(
                size=chart_df["bubble_size"],
                color=chart_df["color"],
                opacity=0.9,
                line=dict(width=1, color="rgba(255,255,255,0.7)"),
            ),
            text=chart_df["label"],
            textposition="middle center",
            textfont=dict(
                size=13,
                color="white",
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Appears in %{customdata[1]} matching jobs"
                "<extra></extra>"
            ),
            customdata=chart_df[["skill", "count"]],
        )
    )

    fig.update_layout(
        height=430,
        margin=dict(l=5, r=5, t=5, b=5),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            visible=False,
            range=[-2.4, 2.4],
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            visible=False,
            range=[-2.5, 2.0],
            scaleanchor="x",
            scaleratio=1,
        ),
    )

    return fig

def create_role_distribution_chart(filtered_jobs: pd.DataFrame):
    """Create horizontal role distribution chart."""
    role_counts_df = (
        filtered_jobs["role_category"]
        .value_counts()
        .reset_index()
    )

    role_counts_df.columns = ["role_category", "job_count"]

    role_counts_df = role_counts_df.sort_values(
        by="job_count",
        ascending=True,
    )

    return (
        alt.Chart(role_counts_df)
        .mark_bar()
        .encode(
            x=alt.X("job_count:Q", title="Job Count"),
            y=alt.Y("role_category:N", sort=None, title="Role Category"),
            tooltip=["role_category", "job_count"],
        )
        .properties(height=260)
    )

def get_tag_placeholder(session_key: str, default_tags: list[str], placeholder: str) -> str:
    """Show placeholder only when the tag input is empty."""
    current_tags = st.session_state.get(session_key, default_tags)

    if current_tags:
        return ""

    return placeholder

def main() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                        "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
        }

        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4,
        .stApp h5,
        .stApp h6,
        .stApp p,
        .stApp label,
        .stApp button,
        .stApp input,
        .stApp textarea,
        .stApp select {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                        "SF Pro Text", "Helvetica Neue", Arial, sans-serif !important;
        }

        .stMarkdown,
        .stText,
        .stDataFrame,
        .stMetric,
        .stSelectbox,
        .stTextInput,
        .stTextArea,
        .stButton {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                        "SF Pro Text", "Helvetica Neue", Arial, sans-serif !important;
        }

        /* Do not override Streamlit / Material icon fonts */
        .material-icons,
        .material-icons-outlined,
        .material-icons-round,
        .material-symbols-outlined,
        .material-symbols-rounded,
        [class*="Icon"],
        [data-testid="stIcon"] {
            font-family: "Material Symbols Rounded", "Material Symbols Outlined",
                        "Material Icons", sans-serif !important;
        }

        .tag-chip {
            padding: 9px 12px;
            margin-bottom: 7px;
            border-radius: 999px;
            background: rgba(37, 99, 235, 0.12);
            border: 1px solid rgba(37, 99, 235, 0.28);
            color: var(--text-color);
            font-size: 14px;
            font-weight: 600;
            line-height: 1.2;
        }

        section[data-testid="stSidebar"] button {
            border-radius: 999px;
        }

        div[data-baseweb="tag"] {
            background-color: rgba(148, 163, 184, 0.16) !important;
            border: 1px solid rgba(148, 163, 184, 0.35) !important;
            border-radius: 999px !important;
            color: var(--text-color) !important;
            font-weight: 500 !important;
            padding: 6px 10px !important;
        }

        div[data-baseweb="tag"] span {
            color: var(--text-color) !important;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                        "SF Pro Text", "Helvetica Neue", Arial, sans-serif !important;
        }

        div[data-baseweb="tag"] svg {
            color: var(--text-color) !important;
            opacity: 0.65 !important;
        }

        div[data-baseweb="tag"]:hover {
            background-color: rgba(148, 163, 184, 0.24) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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

        location = st.text_input(
            "Location",
            value="Toronto ON",
        )

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
    learning_priorities_df = get_learning_priorities(role_scores_df)

    avg_weighted_score = round(role_scores_df["weighted_match_score"].mean(), 2)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Matching Jobs", len(filtered_jobs))

    with col2:
        st.metric("Role Categories", filtered_jobs["role_category"].nunique())

    with col3:
        st.metric("Average Match", f"{avg_weighted_score}%")

    with col4:
        st.metric("Current Skills", len(user_skills))

    st.divider()

    show_role_summary_cards(role_scores_df)

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

    st.dataframe(
        filtered_jobs[
            [
                "title",
                "company",
                "location",
                "experience_level",
                "role_category",
                "skills_text",
            ]
        ],
        use_container_width=True,
    )


if __name__ == "__main__":
    main()