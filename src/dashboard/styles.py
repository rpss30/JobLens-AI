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

        section[data-testid="stSidebar"]
        div[data-testid="stTextInput"]:has(input[aria-label="Search jobs"])
        div[data-testid="stTextInputRootElement"] {
            min-height: 3.75rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stTextInput"]:has(input[aria-label="Search jobs"])
        input[aria-label="Search jobs"] {
            height: 3.625rem !important;
            padding-top: 0.45rem !important;
            padding-bottom: 1.55rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stTextInput"]:has(input[aria-label="Search jobs"])
        div[data-testid="stTextInputRootElement"]
        > div:has(span[data-testid="stTextInputIcon"]) {
            height: 2.25rem !important;
            align-self: flex-start !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stTextInput"]:has(input[aria-label="Search jobs"])
        div[data-testid="InputInstructions"] {
            bottom: 0.2rem !important;
            right: 0.55rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.dataset-info-popover-anchor),
        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.postgres-toggle-marker) {
            display: none !important;
        }

        div[data-testid="stElementContainer"]:has(.active-dataset-button-marker) {
            display: none !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.dataset-info-popover-anchor)
        + div button[data-testid="stPopoverButton"] {
            width: 3.35rem !important;
            min-width: 3.35rem !important;
            height: 2.45rem !important;
            padding: 0 0.55rem !important;
            justify-content: center !important;
            gap: 0.12rem !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.dataset-info-popover-anchor)
        + div button[data-testid="stPopoverButton"] p {
            display: none !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.postgres-toggle-off)
        + div[data-testid="stElementContainer"] div.stButton > button {
            background: rgba(220, 38, 38, 0.08) !important;
            border-color: rgba(220, 38, 38, 0.72) !important;
            color: #b91c1c !important;
            font-weight: 700 !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.postgres-toggle-off)
        + div[data-testid="stElementContainer"] div.stButton > button:hover {
            background: rgba(220, 38, 38, 0.14) !important;
            border-color: #dc2626 !important;
            color: #991b1b !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.postgres-toggle-on)
        + div[data-testid="stElementContainer"] div.stButton > button {
            background: rgba(22, 163, 74, 0.10) !important;
            border-color: rgba(22, 163, 74, 0.72) !important;
            color: #166534 !important;
            font-weight: 700 !important;
        }

        section[data-testid="stSidebar"]
        div[data-testid="stElementContainer"]:has(.postgres-toggle-on)
        + div[data-testid="stElementContainer"] div.stButton > button:hover {
            background: rgba(22, 163, 74, 0.16) !important;
            border-color: #16a34a !important;
            color: #14532d !important;
        }

        div[data-testid="stElementContainer"]:has(.active-dataset-button-marker)
        + div[data-testid="stElementContainer"] div.stButton > button,
        div[data-testid="stElementContainer"]:has(.active-dataset-button-marker)
        + div[data-testid="stElementContainer"] div.stButton > button:disabled {
            background: rgba(22, 163, 74, 0.10) !important;
            border-color: rgba(22, 163, 74, 0.72) !important;
            color: #166534 !important;
            cursor: default !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }

        div[data-testid="stElementContainer"]:has(.active-dataset-button-marker)
        + div[data-testid="stElementContainer"] div.stButton > button *,
        div[data-testid="stElementContainer"]:has(.active-dataset-button-marker)
        + div[data-testid="stElementContainer"] div.stButton > button:disabled * {
            color: #166534 !important;
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

        .candidate-summary-card {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 18px;
            padding: 1.15rem 1.35rem;
            margin-top: 0.75rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
        }

        .candidate-summary-text {
            font-size: 1.03rem;
            line-height: 1.65;
            margin: 0;
            color: var(--text-color);
        }

        .summary-highlight {
            display: inline-block;
            padding: 0.08rem 0.45rem;
            border-radius: 999px;
            background: rgba(37, 99, 235, 0.10);
            border: 1px solid rgba(37, 99, 235, 0.18);
            color: #2563eb;
            font-weight: 750;
        }

        .summary-positive {
            color: #15803d;
            font-weight: 750;
        }

        .summary-warning {
            color: #b45309;
            font-weight: 750;
        }

        .job-card {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 18px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
        }

        .job-card-header {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
        }

        .job-card-title {
            font-size: 1.1rem;
            line-height: 1.35;
            margin: 0;
            color: var(--text-color);
        }

        .job-card-company {
            margin: 0.25rem 0 0 0;
            color: rgba(100, 116, 139, 0.95);
            font-size: 0.92rem;
        }

        .job-card-score {
            min-width: 72px;
            text-align: center;
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            background: rgba(37, 99, 235, 0.10);
            border: 1px solid rgba(37, 99, 235, 0.20);
            color: #2563eb;
            font-weight: 700;
            font-size: 0.95rem;
        }

        .job-card-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.85rem;
            margin-bottom: 1rem;
        }

        .job-card-meta span {
            border-radius: 999px;
            padding: 0.25rem 0.65rem;
            background: rgba(148, 163, 184, 0.14);
            border: 1px solid rgba(148, 163, 184, 0.24);
            color: var(--text-color);
            font-size: 0.82rem;
            font-weight: 500;
        }

        .job-card-skills {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        .job-card-label {
            margin: 0 0 0.25rem 0;
            font-size: 0.78rem;
            font-weight: 700;
            color: rgba(100, 116, 139, 0.95);
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        .job-card-positive,
        .job-card-negative {
            margin: 0;
            font-size: 0.9rem;
            line-height: 1.5;
            color: var(--text-color);
        }

        .job-card-footer {
            display: flex;
            gap: 0.75rem;
            margin-top: 1rem;
            color: rgba(100, 116, 139, 0.95);
            font-size: 0.82rem;
        }

        /* Metric card text sizing */
        div[data-testid="stMetric"] {
            padding-top: 0.15rem;
            padding-bottom: 0.15rem;
        }

        div[data-testid="stMetricLabel"] p {
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            line-height: 1.2 !important;
            white-space: normal !important;
        }

        div[data-testid="stMetricValue"] > div {
            font-size: 1.55rem !important;
            line-height: 1.25 !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }

        /* Analyze Jobs primary button */
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: #2563eb !important;
            color: white !important;
            border: 1px solid #2563eb !important;
            border-radius: 999px !important;
            font-weight: 700 !important;
        }

        section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {
            background: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
