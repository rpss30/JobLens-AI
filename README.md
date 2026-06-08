# JobLens AI

JobLens AI is a personalized job market intelligence dashboard that helps candidates understand how well their current skills align with target roles.

The dashboard analyzes job postings, extracts required technical skills, groups roles into market categories, calculates role-specific match scores, and recommends high-impact skills to learn next.

Current MVP uses a curated sample dataset of job postings to simulate role-specific market analysis. The app can run from the local processed CSV dataset or from a local PostgreSQL database seeded with processed job data. Future iterations will expand to larger real-world ingestion pipelines.


## Live Demo

[View the live dashboard](https://joblens-ai-rpss-30.streamlit.app/)

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
- Optional PostgreSQL-backed data loading with CSV fallback
- Local database seeding script for processed job postings
- Custom CSV upload validation and error handling



## Role Categories

JobLens AI currently groups jobs into the following role categories:

- AI/ML
- Data Science
- Data Engineering
- Cloud/AWS
- Software Engineering
- Analytics
- Other



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



## How Matching Works

JobLens AI extracts technical skills from job descriptions using a configurable skill dictionary.

The matching engine calculates two types of scores:

### Unweighted Match Score

Treats every required skill equally.

### Weighted Match Score

Uses role-specific skill weights so that more important skills matter more for each role category.

For example, Python, PyTorch, TensorFlow, model deployment, and MLflow may matter more for AI/ML roles, while AWS, Docker, Terraform, Lambda, and CloudWatch may matter more for Cloud/AWS roles.

This helps avoid the "big pond problem," where a candidate appears to match a role just because they know many minor tools, even if they are missing the most important skills.



## Role-Specific Skill Weighting

Skill weights are generated from the job dataset instead of being manually hardcoded.

For each role category, JobLens AI:

1. Counts how often each skill appears across relevant postings.
2. Converts skill frequency into a role-specific weight.
3. Applies smoothing based on sample size so small categories do not produce unrealistic weights.
4. Uses those weights to calculate weighted candidate fit.

This keeps the scoring system data-driven while still being simple enough to explain in a demo.



## Custom CSV Upload

The dashboard supports uploading a custom job postings CSV.

Required columns:

- `title`
- `company`
- `location`
- `description`
- `experience_level`

Example:

```csv
title,company,location,description,experience_level
Data Scientist,TestCo,Toronto ON,"Analyze data using Python, SQL, Pandas, statistics, dashboards, and scikit-learn.",Entry Level
Cloud Engineer,CloudTest,Vancouver BC,"Build AWS infrastructure using Docker, Terraform, Lambda, S3, EC2, and CloudWatch.",Entry Level
Backend Developer,APITest,Montreal QC,"Build REST APIs using Python, PostgreSQL, Docker, AWS, and CI/CD.",Entry Level
```

A sample upload file is available at:

```text
data/examples/sample_upload_jobs.csv
```

Uploaded CSVs are processed during the active Streamlit session and are not persisted as permanent storage.



## Tech Stack

- Python
- Pandas
- Streamlit
- Altair
- Plotly
- PostgreSQL
- SQLAlchemy
- psycopg
- pytest
- GitHub Actions
- Streamlit Cloud

Planned future additions:

- FastAPI
- Docker
- AWS



## Project Structure

```text
JobLens AI
├── data
│   ├── raw
│   │   └── sample_jobs.csv
│   ├── processed
│   │   └── processed_jobs.csv
│   └── examples
│       └── sample_upload_jobs.csv
├── scripts
│   └── seed_database.py
├── src
│   ├── config
│   │   └── skills.py
│   ├── database
│   │   ├── db.py
│   │   ├── init_db.py
│   │   ├── models.py
│   │   └── repository.py
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
├── .github
│   └── workflows
│       └── tests.yml
├── .streamlit
│   └── config.toml
├── .env.example
├── requirements.txt
└── README.md
```



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



## Local PostgreSQL Setup

JobLens AI can run with either the default processed CSV dataset or a local PostgreSQL database.

The PostgreSQL integration is optional. If the database is unavailable, the Streamlit dashboard falls back to the local processed CSV file.

### 1. Install PostgreSQL

On macOS with Homebrew:

```bash
brew install postgresql@16
brew services start postgresql@16
```

Check that PostgreSQL is available:

```bash
psql --version
```

### 2. Create a local database

```bash
createdb joblens_ai
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg://localhost:5432/joblens_ai
```

Do not commit `.env`.

A safe template is included in:

```text
.env.example
```

### 4. Create database tables

```bash
python -m src.database.init_db
```

### 5. Seed the database

Load the existing processed sample jobs into PostgreSQL:

```bash
python -m scripts.seed_database
```

Expected output:

```text
Database tables created successfully.
Seeded <number> processed jobs into PostgreSQL.
```

### 6. Run the dashboard

```bash
streamlit run src/dashboard/app.py
```

In the sidebar, turn on:

```text
Use PostgreSQL database
```

If PostgreSQL is connected and seeded correctly, the sidebar will show that sample jobs were loaded from PostgreSQL. Otherwise, the app will fall back to the local processed CSV.

### Database tables

The current PostgreSQL schema includes:

- `datasets`
- `job_postings`
- `processed_jobs`
- `skills`
- `job_skills`

This keeps the current MVP simple while preparing the project for future saved datasets, skill trend snapshots, analysis history, and real job ingestion.


## Testing

Run the test suite locally:

```bash
pytest
```
The project includes tests for dashboard service logic, matching behavior, role-specific weighting, CSV upload validation, and database helper utilities.

Tests are also run automatically through GitHub Actions on pushes and pull requests.


## Current Status

This project is currently a polished MVP focused on dashboard experience, role-specific scoring, skill-gap analysis, CSV upload support, and optional PostgreSQL-backed data loading.

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
- Custom CSV upload with validation
- PostgreSQL database schema
- PostgreSQL seeding script for processed jobs
- Optional PostgreSQL dashboard loading with CSV fallback
- pytest test suite
- GitHub Actions test workflow
- Streamlit Cloud deployment

Not built yet:

- Real job scraping or external job ingestion
- Saved uploaded datasets in PostgreSQL
- Saved analysis runs
- FastAPI backend
- Dockerized deployment
- Authentication or multi-user support
- Production-grade NLP role classification



## Known Limitations

- The current MVP uses a curated sample dataset instead of live job postings.
- Skill extraction is dictionary-based, so it may miss aliases or uncommon phrasing.
- Role classification is rule-based and title-first, not ML-based yet.
- Match scores are designed for explainability, not as a production hiring recommendation system.
- PostgreSQL support is currently local-first and optional; uploaded CSVs are still processed only during the active Streamlit session.



## Future Improvements

Planned next steps:

- Add real job ingestion from public job sources or APIs
- Persist uploaded datasets and saved analysis runs in PostgreSQL
- Add FastAPI endpoints for matching and recommendations
- Add Docker support
- Add AWS deployment option beyond the current Streamlit Cloud deployment
- Improve skill alias matching for terms like `JS`, `JavaScript`, `Node`, and `Node.js`
- Add trend analysis for skills by role and location
- Add downloadable candidate skill-gap reports



## Why This Project Matters

JobLens AI is designed to be a practical portfolio project that combines data processing, analytics, dashboard design, and matching logic.

It demonstrates:

- Building a data pipeline from raw job postings
- Extracting structured skills from unstructured text
- Designing role-specific scoring logic
- Creating an interactive analytics dashboard
- Turning raw data into useful product insights
- Communicating technical results in a user-friendly way
