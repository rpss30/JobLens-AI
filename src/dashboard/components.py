# src/dashboard/components.py

from html import escape
from textwrap import dedent

import pandas as pd
import streamlit as st

from src.dashboard.services import get_positive_job_matches


def build_job_card_footer_html(
    *,
    matched_count: int,
    missing_count: int,
    search_relevance: float | None = None,
) -> str:
    """Build compact footer markup without breaking the surrounding HTML block."""
    footer_items = [
        f"<span>{matched_count} matched</span>",
        f"<span>{missing_count} missing</span>",
    ]

    if search_relevance is not None:
        footer_items.append(
            f"<span>{search_relevance:.1f}% relevant</span>"
        )

    return "".join(footer_items)


def show_role_summary_cards(role_scores_df: pd.DataFrame) -> None:
    """Show top role matches as metric cards."""
    st.subheader("Best Role Matches")

    if role_scores_df.empty or "weighted_match_score" not in role_scores_df.columns:
        st.info("No role match scores are available yet.")
        return

    positive_roles = role_scores_df[
        role_scores_df["weighted_match_score"] > 0
    ]

    if positive_roles.empty:
        st.info(
            "No role categories have a positive skill match yet. "
            "Review the recommended skills and role breakdown for gaps."
        )
        return

    top_roles = positive_roles.head(3)
    cols = st.columns(3)

    for col, (_, row) in zip(cols, top_roles.iterrows()):
        with col:
            representative_job_count = int(
                row.get("representative_job_count", 0)
            )
            st.metric(
                label=row["role_category"],
                value=f"{row['weighted_match_score']}%",
                delta=(
                    f"{row.get('sample_confidence', 'N/A')} confidence, "
                    f"{representative_job_count} representative "
                    f"{'job' if representative_job_count == 1 else 'jobs'}"
                ),
            )


def show_role_explanations(role_scores_df: pd.DataFrame) -> None:
    """Show compact explanation cards for the top role matches."""
    st.subheader("Why These Roles Match")
    st.caption("Highlights the strongest matching skills and the biggest gaps for your top role categories.")

    if role_scores_df.empty or "weighted_match_score" not in role_scores_df.columns:
        st.info("No role match explanations are available yet.")
        return

    positive_roles = role_scores_df[
        role_scores_df["weighted_match_score"] > 0
    ]

    if positive_roles.empty:
        st.info(
            "There are no positive role matches to explain yet. "
            "The detailed breakdown below still shows the underlying gaps."
        )
        return

    top_roles = positive_roles.head(3)

    for _, row in top_roles.iterrows():
        role_weights = row["role_skill_weights"]

        matched_ranked = sorted(
            row["matched_skills"],
            key=lambda skill: role_weights.get(skill, 1),
            reverse=True,
        )[:5]

        missing_ranked = sorted(
            row["missing_skills"],
            key=lambda skill: role_weights.get(skill, 1),
            reverse=True,
        )[:5]

        with st.container():
            st.markdown(
                f"### {row['role_category']} — "
                f"{row['weighted_match_score']}% role skill fit"
            )

            col1, col2, col3 = st.columns([1.2, 1.2, 0.8])

            with col1:
                st.write("**Strong matches**")
                if matched_ranked:
                    st.write(", ".join(matched_ranked))
                else:
                    st.write("No major matches yet.")

            with col2:
                st.write("**Biggest gaps**")
                if missing_ranked:
                    st.write(", ".join(missing_ranked))
                else:
                    st.write("No major missing skills.")

            with col3:
                st.write("**Context**")
                st.write(f"Jobs analyzed: {row['sample_size']}")
                st.write(
                    "Representative jobs: "
                    f"{row.get('representative_job_count', 0)}"
                )
                st.write(
                    f"Confidence: {row.get('sample_confidence', 'N/A')}"
                )
                st.write(f"Unweighted: {row['unweighted_match_score']}%")

def show_candidate_fit_summary(candidate_summary: dict) -> None:
    """Show a natural-language explanation of the candidate's fit."""

    st.subheader("Candidate Fit Summary")

    summary_text = candidate_summary.get("summary", "")

    st.markdown(
        f"""
        <div class="candidate-summary-card">
            <p class="candidate-summary-text">
                {summary_text}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    matched_skills = candidate_summary.get("matched_skills", [])
    missing_skills = candidate_summary.get("missing_skills", [])

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Current strengths**")
        if matched_skills:
            st.write(", ".join(matched_skills))
        else:
            st.write("No major matched skills yet.")

    with col2:
        st.markdown("**Highest-impact gaps**")
        if missing_skills:
            st.write(", ".join(missing_skills))
        else:
            st.write("No major gaps found.")

def show_top_job_match_cards(
    job_match_details_df: pd.DataFrame,
    top_n: int = 5,
) -> None:
    """Show top matching job postings as product-style cards."""

    has_search_relevance = (
        "search_relevance" in job_match_details_df.columns
        and job_match_details_df["search_relevance"].gt(0).any()
    )
    st.subheader(
        "Relevant Job Matches"
        if has_search_relevance
        else "Top Matching Jobs"
    )
    positive_job_matches_df = get_positive_job_matches(job_match_details_df)
    positive_match_count = len(positive_job_matches_df)
    filtered_job_count = len(job_match_details_df)

    caption = (
        f"Showing {positive_match_count} positive skill "
        f"{'match' if positive_match_count == 1 else 'matches'} from "
        f"{filtered_job_count} filtered "
        f"{'posting' if filtered_job_count == 1 else 'postings'}. "
        "Zero-overlap postings are omitted."
    )
    if has_search_relevance:
        caption += (
            " Results are ordered by text relevance; card scores show "
            "candidate skill fit."
        )
    st.caption(caption)

    if positive_job_matches_df.empty:
        st.info(
            "No positive job-level matches found yet. "
            "The filtered postings are still available in the table below."
        )
        return

    top_jobs = positive_job_matches_df.head(top_n)

    for _, row in top_jobs.iterrows():
        title = escape(str(row.get("title", "Untitled Role")))
        company = escape(str(row.get("company", "Unknown Company")))
        location = escape(str(row.get("location", "Unknown Location")))
        experience_level = escape(str(row.get("experience_level", "N/A")))
        role_category = escape(str(row.get("role_category", "Other")))
        job_match_score = row.get("job_match_score", 0)
        search_relevance = float(row.get("search_relevance", 0))

        matched_skills = escape(
            str(row.get("matched_skills_preview", "None"))
        )
        related_skills = str(row.get("related_skills_preview", "None"))
        missing_skills = escape(
            str(row.get("missing_skills_preview", "None"))
        )
        matched_count = row.get("matched_skills_count", 0)
        missing_count = row.get("missing_skills_count", 0)
        source_url = str(row.get("source_url", "")).strip()
        footer_html = build_job_card_footer_html(
            matched_count=matched_count,
            missing_count=missing_count,
            search_relevance=(
                search_relevance
                if has_search_relevance
                else None
            ),
        )

        card_html = dedent(
            f"""
            <div class="job-card">
                <div class="job-card-header">
                    <div>
                        <h3 class="job-card-title">{title}</h3>
                        <p class="job-card-company">{company}</p>
                    </div>
                    <div class="job-card-score">
                        {job_match_score}%
                    </div>
                </div>
                <div class="job-card-meta">
                    <span>{location}</span>
                    <span>{experience_level}</span>
                    <span>{role_category}</span>
                </div>
                <div class="job-card-skills">
                    <div>
                        <p class="job-card-label">Matched skills</p>
                        <p class="job-card-positive">{matched_skills}</p>
                    </div>
                    <div>
                        <p class="job-card-label">Missing skills</p>
                        <p class="job-card-negative">{missing_skills}</p>
                    </div>
                </div>
                <div class="job-card-footer">
                    {footer_html}
                </div>
            </div>
            """
        ).strip()

        st.markdown(card_html, unsafe_allow_html=True)

        if related_skills != "None":
            st.caption(f"Related-skill credit: {related_skills}")

        if source_url.startswith(("https://", "http://")):
            st.link_button(
                "View original posting",
                source_url,
                icon=":material/open_in_new:",
            )
