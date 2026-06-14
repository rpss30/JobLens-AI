## Data Ingestion (Legacy)

The previous ingestion pipeline (including Adzuna API and LLM-based extraction scripts) has been removed as part of a simplification and CI speed optimization effort.

### Current Data Flow

JobLens AI now operates exclusively on curated or user-provided datasets:

- **Processed CSV datasets** (local development and demo data)
- **PostgreSQL dataset storage** (persistent dataset management and saved analysis runs)
- **Uploaded CSV ingestion via dashboard** (runtime user-provided datasets processed on demand)

### Design Decision

This change was made to:

- Reduce CI complexity and runtime overhead
- Eliminate external API dependencies during tests
- Ensure deterministic and reproducible job analysis outputs
- Centralize all preprocessing within the `job_processor.py` pipeline

### Future Direction (Optional)

External ingestion sources (e.g., job APIs or LLM-based enrichment) may be reintroduced later as modular plugins, but are intentionally excluded from the current MVP scope.