from src.database.models import (
    AnalysisRun,
    Dataset,
    ExtractionResult,
    IngestionRun,
    JobPosting,
    ProcessedJob,
)


def table_index_names(model) -> set[str]:
    return {index.name for index in model.__table__.indexes}


def table_constraint_names(model) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if constraint.name
    }


def test_job_postings_define_duplicate_prevention_constraints() -> None:
    constraint_names = table_constraint_names(JobPosting)

    assert "uq_job_posting_dataset_job_id" in constraint_names
    assert "uq_job_posting_dataset_source_url" in constraint_names


def test_common_query_paths_have_indexes() -> None:
    assert "ix_datasets_source_type_created_at" in table_index_names(Dataset)
    assert "ix_job_postings_dataset_company" in table_index_names(JobPosting)
    assert "ix_job_postings_dataset_location" in table_index_names(JobPosting)
    assert (
        "ix_job_postings_dataset_experience_level"
        in table_index_names(JobPosting)
    )
    assert "ix_processed_jobs_role_category" in table_index_names(ProcessedJob)
    assert (
        "ix_analysis_runs_dataset_name_created_at"
        in table_index_names(AnalysisRun)
    )


def test_pipeline_tracking_tables_have_operational_indexes() -> None:
    assert "ix_ingestion_runs_status_started_at" in table_index_names(IngestionRun)
    assert (
        "ix_extraction_results_provider_created_at"
        in table_index_names(ExtractionResult)
    )
