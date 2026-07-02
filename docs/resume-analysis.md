# Resume Analysis

JobLens AI supports optional paste-in resume analysis for candidate-role fit.
The feature is designed to improve product usefulness without turning the app
into a resume storage system.

## Privacy Boundary

- Raw resume text is analyzed in memory for the active request only.
- Raw resume text is not saved to PostgreSQL.
- Raw resume text is not returned by the FastAPI response.
- Saved analysis runs store extracted profile skills and summary outputs, not
  pasted resume text.
- Tests assert that API responses and dashboard saved-run calls do not include
  raw resume text.

## Implementation

The deterministic resume analyzer lives in:

```text
src/resume/resume_analyzer.py
```

It extracts:

- known JobLens skills from a controlled taxonomy,
- common aliases such as `Postgres`, `Node.js`, `CI/CD`, and `sklearn`,
- experience areas such as backend engineering, data engineering, cloud/devops,
  analytics, machine learning, and frontend engineering,
- project keywords such as API development, deployment, monitoring, dashboards,
  data pipelines, and experimentation.

The analyzer merges user-selected skills with resume-derived skills, then uses
the existing weighted skill-fit engine and local semantic profile similarity to
rank jobs.

## Outputs

Resume analysis returns:

- numeric resume fit score,
- extracted resume skills,
- combined profile skills,
- experience areas,
- project keywords,
- matched skills,
- missing skills,
- learning priorities,
- suggested resume keywords,
- top resume-matched jobs,
- deterministic explanations.

Suggested resume keywords are intentionally conservative. They are market
signals from matching postings, not instructions to add skills the candidate
does not actually have.

## API Usage

`POST /analyze` accepts an optional `resume_text` field. When resume text is
provided, the response includes `resume_analysis`.

```json
{
  "current_skills": [],
  "resume_text": "Built FastAPI REST APIs with Python, PostgreSQL, Docker, AWS, and CI/CD.",
  "target_roles": [],
  "search_query": "",
  "location": "Any",
  "experience_level": "Any",
  "top_n": 5
}
```

Resume text can be used without manually selected skills or a search query. In
that case JobLens compares the resume profile against the selected dataset.

## Tradeoffs

- Paste-in text is implemented before PDF/DOCX parsing to avoid unsafe file
  upload complexity in the first resume-analysis iteration.
- The analyzer uses deterministic taxonomy and alias matching instead of an LLM
  so tests remain offline and reproducible.
- The feature does not persist private resume content; this means saved runs
  cannot reconstruct the original resume text later.
