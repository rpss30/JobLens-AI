"""Streamlit-facing view of the shared job analysis helpers.

The analysis logic itself lives in src.analysis.job_services, which imports no
web framework, so the FastAPI service can use it without pulling Streamlit into
the API process. This module adds the Streamlit caching the dashboard depends on
and keeps the historical `src.dashboard.services` import path working.

The wildcard re-export is deliberate: this is a compatibility surface, and
listing every helper here would mean editing two files each time one is added.
"""

import pandas as pd
import streamlit as st

from src.analysis.job_services import *  # noqa: F401,F403
from src.analysis.job_services import (
    load_processed_jobs as _load_processed_jobs,
    load_processed_jobs_from_csv as _load_processed_jobs_from_csv,
)


@st.cache_data
def load_processed_jobs() -> pd.DataFrame:
    """Load and process job data once per Streamlit session."""
    return _load_processed_jobs()


@st.cache_data
def load_processed_jobs_from_csv(path: str) -> pd.DataFrame:
    """Load an already-processed jobs CSV once per Streamlit session."""
    return _load_processed_jobs_from_csv(path)
