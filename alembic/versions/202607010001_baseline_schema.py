"""baseline schema before managed migrations

Revision ID: 202607010001
Revises:
Create Date: 2026-07-01 00:01:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202607010001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_datasets_id"), "datasets", ["id"], unique=False)

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name"),
    )
    op.create_index(op.f("ix_skills_id"), "skills", ["id"], unique=False)

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dataset_name", sa.String(length=255), nullable=False),
        sa.Column(
            "target_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("experience_level", sa.String(length=100), nullable=False),
        sa.Column(
            "current_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("best_role", sa.String(length=100), nullable=True),
        sa.Column("weighted_match_score", sa.Float(), nullable=True),
        sa.Column("top_missing_skill", sa.String(length=100), nullable=True),
        sa.Column("jobs_analyzed", sa.Integer(), nullable=False),
        sa.Column(
            "recommended_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "role_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_runs_id"), "analysis_runs", ["id"], unique=False)

    op.create_table(
        "job_postings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("experience_level", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_postings_id"), "job_postings", ["id"], unique=False)

    op.create_table(
        "processed_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_posting_id", sa.Integer(), nullable=False),
        sa.Column("clean_title", sa.String(length=255), nullable=False),
        sa.Column("clean_description", sa.Text(), nullable=False),
        sa.Column("role_category", sa.String(length=100), nullable=False),
        sa.Column(
            "extracted_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("skills_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_posting_id"], ["job_postings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_posting_id"),
    )
    op.create_index(op.f("ix_processed_jobs_id"), "processed_jobs", ["id"], unique=False)

    op.create_table(
        "job_skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("processed_job_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["processed_job_id"], ["processed_jobs.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("processed_job_id", "skill_id", name="uq_job_skill"),
    )
    op.create_index(op.f("ix_job_skills_id"), "job_skills", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_skills_id"), table_name="job_skills")
    op.drop_table("job_skills")

    op.drop_index(op.f("ix_processed_jobs_id"), table_name="processed_jobs")
    op.drop_table("processed_jobs")

    op.drop_index(op.f("ix_job_postings_id"), table_name="job_postings")
    op.drop_table("job_postings")

    op.drop_index(op.f("ix_analysis_runs_id"), table_name="analysis_runs")
    op.drop_table("analysis_runs")

    op.drop_index(op.f("ix_skills_id"), table_name="skills")
    op.drop_table("skills")

    op.drop_index(op.f("ix_datasets_id"), table_name="datasets")
    op.drop_table("datasets")
