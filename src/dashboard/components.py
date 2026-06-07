# src/dashboard/components.py

import pandas as pd
import streamlit as st


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


def show_role_explanations(role_scores_df: pd.DataFrame) -> None:
    """Show compact explanation cards for the top role matches."""
    st.subheader("Why These Roles Match")
    st.caption("Highlights the strongest matching skills and the biggest gaps for your top role categories.")

    top_roles = role_scores_df.head(3)

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
                f"### {row['role_category']} — {row['weighted_match_score']}% weighted match"
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
                st.write(f"Unweighted: {row['unweighted_match_score']}%")
                st.write(f"Score: {row['matched_weight']} / {row['total_possible_weight']}")

def show_candidate_fit_summary(candidate_summary: dict) -> None:
    """Show a natural-language explanation of the candidate's fit."""

    st.subheader("Candidate Fit Summary")

    st.markdown(
        f"""
        <div class="candidate-summary-card">
            <p class="candidate-summary-text">
                {candidate_summary["summary"]}
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