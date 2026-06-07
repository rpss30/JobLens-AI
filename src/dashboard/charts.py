# src/dashboard/charts.py

import altair as alt
import plotly.graph_objects as go
import pandas as pd


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


def create_recommended_skills_chart(recommended_skills_df: pd.DataFrame):
    """Create horizontal bar chart for recommended skills to learn."""
    if recommended_skills_df.empty:
        return None

    chart_df = recommended_skills_df.head(10).sort_values(
        by="score",
        ascending=True,
    )

    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("score:Q", title="Learning Priority Score"),
            y=alt.Y("skill:N", sort=None, title="Skill"),
            tooltip=[
                alt.Tooltip("skill:N", title="Skill"),
                alt.Tooltip("score:Q", title="Priority Score"),
                alt.Tooltip("job_count:Q", title="Jobs Requiring Skill"),
                alt.Tooltip("avg_weight:Q", title="Average Role Weight", format=".2f"),
            ],
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

def create_jobs_by_location_chart(location_counts_df: pd.DataFrame):
    """Create horizontal bar chart for jobs grouped by location."""

    if location_counts_df.empty:
        return None

    chart_df = location_counts_df.sort_values(
        by="job_count",
        ascending=True,
    )

    return (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("job_count:Q", title="Job Count"),
            y=alt.Y("location:N", sort=None, title="Location"),
            tooltip=[
                alt.Tooltip("location:N", title="Location"),
                alt.Tooltip("job_count:Q", title="Jobs"),
            ],
        )
        .properties(height=260)
    )