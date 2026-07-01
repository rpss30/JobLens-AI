"""add source metadata tracking and query indexes

Revision ID: 202607010002
Revises: 202607010001
Create Date: 2026-07-01 00:02:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202607010002"
down_revision = "202607010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_postings", sa.Column("source", sa.String(length=50), nullable=True))
    op.add_column(
        "job_postings",
        sa.Column("source_url", sa.String(length=1000), nullable=True),
    )
    op.add_column("job_postings", sa.Column("fetched_at", sa.DateTime(), nullable=True))
    op.add_column(
        "job_postings",
        sa.Column("date_posted", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("valid_through", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("employment_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("workplace_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column(
            "is_remote",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("job_postings", "is_remote", server_default=None)
    op.add_column(
        "job_postings",
        sa.Column("address_locality", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("address_region", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("address_country", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "job_postings",
        sa.Column("source_updated_at", sa.String(length=100), nullable=True),
    )

    op.add_column(
        "processed_jobs",
        sa.Column("skill_extraction_provider", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "processed_jobs",
        sa.Column("skill_extraction_error", sa.Text(), nullable=True),
    )

    op.create_unique_constraint(
        "uq_job_posting_dataset_job_id",
        "job_postings",
        ["dataset_id", "job_id"],
    )
    op.create_unique_constraint(
        "uq_job_posting_dataset_source_url",
        "job_postings",
        ["dataset_id", "source_url"],
    )

    op.create_index(
        "ix_datasets_source_type_created_at",
        "datasets",
        ["source_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_job_postings_dataset_company",
        "job_postings",
        ["dataset_id", "company"],
        unique=False,
    )
    op.create_index(
        "ix_job_postings_dataset_location",
        "job_postings",
        ["dataset_id", "location"],
        unique=False,
    )
    op.create_index(
        "ix_job_postings_dataset_experience_level",
        "job_postings",
        ["dataset_id", "experience_level"],
        unique=False,
    )
    op.create_index(
        "ix_job_postings_dataset_source",
        "job_postings",
        ["dataset_id", "source"],
        unique=False,
    )
    op.create_index(
        "ix_job_postings_dataset_fetched_at",
        "job_postings",
        ["dataset_id", "fetched_at"],
        unique=False,
    )
    op.create_index(
        "ix_processed_jobs_role_category",
        "processed_jobs",
        ["role_category"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_runs_dataset_created_at",
        "analysis_runs",
        ["dataset_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_runs_dataset_name_created_at",
        "analysis_runs",
        ["dataset_name", "created_at"],
        unique=False,
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_sources", sa.Integer(), nullable=False),
        sa.Column("successful_sources", sa.Integer(), nullable=False),
        sa.Column("failed_sources", sa.Integer(), nullable=False),
        sa.Column("raw_job_count", sa.Integer(), nullable=False),
        sa.Column("processed_job_count", sa.Integer(), nullable=False),
        sa.Column(
            "error_log",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_runs_id"), "ingestion_runs", ["id"], unique=False)
    op.create_index(
        "ix_ingestion_runs_dataset_started_at",
        "ingestion_runs",
        ["dataset_id", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_runs_status_started_at",
        "ingestion_runs",
        ["status", "started_at"],
        unique=False,
    )

    op.create_table(
        "extraction_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("processed_job_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column(
            "extracted_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["processed_job_id"], ["processed_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_extraction_results_id"),
        "extraction_results",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_results_processed_job_created_at",
        "extraction_results",
        ["processed_job_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_results_provider_created_at",
        "extraction_results",
        ["provider", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_extraction_results_provider_created_at",
        table_name="extraction_results",
    )
    op.drop_index(
        "ix_extraction_results_processed_job_created_at",
        table_name="extraction_results",
    )
    op.drop_index(op.f("ix_extraction_results_id"), table_name="extraction_results")
    op.drop_table("extraction_results")

    op.drop_index("ix_ingestion_runs_status_started_at", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_dataset_started_at", table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_id"), table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index(
        "ix_analysis_runs_dataset_name_created_at",
        table_name="analysis_runs",
    )
    op.drop_index("ix_analysis_runs_dataset_created_at", table_name="analysis_runs")
    op.drop_index("ix_processed_jobs_role_category", table_name="processed_jobs")
    op.drop_index("ix_job_postings_dataset_fetched_at", table_name="job_postings")
    op.drop_index("ix_job_postings_dataset_source", table_name="job_postings")
    op.drop_index(
        "ix_job_postings_dataset_experience_level",
        table_name="job_postings",
    )
    op.drop_index("ix_job_postings_dataset_location", table_name="job_postings")
    op.drop_index("ix_job_postings_dataset_company", table_name="job_postings")
    op.drop_index("ix_datasets_source_type_created_at", table_name="datasets")

    op.drop_constraint(
        "uq_job_posting_dataset_source_url",
        "job_postings",
        type_="unique",
    )
    op.drop_constraint(
        "uq_job_posting_dataset_job_id",
        "job_postings",
        type_="unique",
    )

    op.drop_column("processed_jobs", "skill_extraction_error")
    op.drop_column("processed_jobs", "skill_extraction_provider")

    op.drop_column("job_postings", "source_updated_at")
    op.drop_column("job_postings", "address_country")
    op.drop_column("job_postings", "address_region")
    op.drop_column("job_postings", "address_locality")
    op.drop_column("job_postings", "is_remote")
    op.drop_column("job_postings", "workplace_type")
    op.drop_column("job_postings", "employment_type")
    op.drop_column("job_postings", "valid_through")
    op.drop_column("job_postings", "date_posted")
    op.drop_column("job_postings", "fetched_at")
    op.drop_column("job_postings", "source_url")
    op.drop_column("job_postings", "source")
