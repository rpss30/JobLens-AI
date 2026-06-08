# JobLens AI

JobLens AI is a personalized job market intelligence dashboard that helps candidates understand how well their current skills align with target roles.

The dashboard analyzes job postings, extracts required technical skills, groups roles into market categories, calculates role-specific match scores, and recommends high-impact skills to learn next.

Current MVP uses a curated sample dataset of job postings to simulate role-specific market analysis. Future iterations will expand to larger real-world ingestion pipelines.

---

## Demo Preview

### Role Fit Overview

![Role Fit Overview](assets/screenshots/role-fit-overview.png)

The dashboard summarizes the candidate's best-fit role, weighted match score, top skill gap, number of jobs analyzed, and current skill count.

### Candidate Fit Summary

![Candidate Fit Summary](assets/screenshots/candidate-fit-summary.png)

JobLens AI generates a short natural-language summary explaining the candidate's strongest role fit, existing strengths, and highest-impact missing skills.

### Top Matching Job Cards

![Top Matching Job Cards](assets/screenshots/job-cards.png)

The dashboard highlights the strongest individual job matches using card-based job summaries with match score, company, location, role category, matched skills, and missing skills.

### Market Insights

![Market Insights](assets/screenshots/market-insights.png)

The dashboard also shows market-level insights such as top required skills, role-specific skill importance, jobs by location, top hiring companies, and role distribution.

---

## Features

- Role-specific skill extraction from job descriptions
- Title-first role categorization with description fallback
- Weighted and unweighted role match scoring
- Skill-gap analysis based on selected candidate skills
- Recommended skills ranked by market demand and role importance
- Candidate fit summary with highlighted strengths and gaps
- Top matching job cards with job-level evidence
- Jobs-by-location market insight
- Role distribution and top hiring companies
- Interactive Streamlit dashboard with controlled search presets and profile presets

---

## Role Categories

JobLens AI currently groups jobs into the following role categories:

- AI/ML
- Data Science
- Data Engineering
- Cloud/AWS
- Software Engineering
- Analytics
- Other

---

## Dataset

The current MVP uses a curated sample dataset located at:

```text
data/raw/sample_jobs.csv
```

The dataset includes approximately 60 job postings across Canadian locations such as:

- Toronto, ON
- Vancouver, BC
- Montreal, QC
- Calgary, AB
- Ottawa, ON

Example roles include:

- Machine Learning Engineer
- AI Engineer
- ML Platform Engineer
- Data Scientist
- Data Analyst
- AWS Cloud Engineer
- Cloud Engineer
- Backend Developer
- Software Engineer
- Data Engineer
- Analytics Engineer

The processed dataset is generated at:

```text
data/processed/processed_jobs.csv
```

---

## How Matching Works

JobLens AI extracts technical skills from job descriptions using a configurable skill dictionary.

The matching engine calculates two types of scores:

### Unweighted Match Score

Treats every required skill equally.

### Weighted Match Score

Uses role-specific skill weights so that more important skills matter more for each role category.

For example, Python, PyTorch, TensorFlow, model deployment, and MLflow may matter more for AI/ML roles, while AWS, Docker, Terraform, Lambda, and CloudWatch may matter more for Cloud/AWS roles.

This helps avoid the "big pond problem," where a candidate appears to match a role just because they know many minor tools, even if they are missing the most important skills.

---

## Role-Specific Skill Weighting

Skill weights are generated from the job dataset instead of being manually hardcoded.

For each role category, JobLens AI:

1. Counts how often each skill appears across relevant postings.
2. Converts skill frequency into a role-specific weight.
3. Applies smoothing based on sample size so small categories do not produce unrealistic weights.
4. Uses those weights to calculate weighted candidate fit.

This keeps the scoring system data-driven while still being simple enough to explain in a demo.

---

## Tech Stack

- Python
- Pandas
- Streamlit
- Altair
- Plotly

Planned future additions:

- scikit-learn
- PostgreSQL
- FastAPI
- Docker
- AWS or Streamlit Cloud deployment

---

## Project Structure

```text
JobLens AI
├── data
│   ├── raw
│   │   └── sample_jobs.csv
│   └── processed
│       └── processed_jobs.csv
├── src
│   ├── config
│   │   └── skills.py
│   ├── processing
│   │   └── job_processor.py
│   ├── matching
│   │   └── match_engine.py
│   └── dashboard
│       ├── app.py
│       ├── charts.py
│       ├── components.py
│       ├── services.py
│       └── styles.py
├── tests
├── requirements.txt
└── README.md
```

---

## Running Locally

Clone the repository:

```bash
git clone https://github.com/rpss30/JobLens-AI.git
cd joblens-ai
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit dashboard:

```bash
streamlit run src/dashboard/app.py
```

---

## Current Status

This project is currently an MVP focused on dashboard experience, role-specific scoring, and skill-gap analysis using a curated dataset.

Completed:

- Data processing pipeline
- Skill extraction
- Role categorization
- Weighted matching engine
- Recommended skills logic
- Streamlit dashboard
- Search presets
- Candidate profile presets
- Candidate fit summary
- Top matching job cards
- Jobs-by-location chart
- Role and skill visualizations

Not built yet:

- Real job scraping or external job ingestion
- PostgreSQL database integration
- FastAPI backend
- Dockerized deployment
- Authentication or multi-user support
- Production-grade NLP role classification

---

## Future Improvements

Planned next steps:

- Add real job ingestion from public job sources or APIs
- Store postings and processed skills in PostgreSQL
- Add FastAPI endpoints for matching and recommendations
- Add Docker support
- Deploy the dashboard using Streamlit Cloud or AWS
- Improve skill alias matching for terms like `JS`, `JavaScript`, `Node`, and `Node.js`
- Add trend analysis for skills by role and location
- Add downloadable candidate skill-gap reports

---

## Why This Project Matters

JobLens AI is designed to be a practical new-grad portfolio project that combines data processing, analytics, dashboard design, and matching logic.

It demonstrates:

- Building a data pipeline from raw job postings
- Extracting structured skills from unstructured text
- Designing role-specific scoring logic
- Creating an interactive analytics dashboard
- Turning raw data into useful product insights
- Communicating technical results in a user-friendly way