# src/dashboard/styles.py

import streamlit as st


def inject_global_styles() -> None:
    """Inject global dashboard styles."""
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

        /* Keep Streamlit / Material icon fonts working */
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