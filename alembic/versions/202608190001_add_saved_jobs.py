"""add saved jobs

Revision ID: 202608190001
Revises: 202608050001
Create Date: 2026-08-19 12:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202608190001"
down_revision = "202608050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("dataset_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("company", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("source_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_name",
            "job_id",
            name="uq_saved_jobs_dataset_job",
        ),
    )
    op.create_index(op.f("ix_saved_jobs_id"), "saved_jobs", ["id"])
    op.create_index(
        "ix_saved_jobs_dataset_created_at",
        "saved_jobs",
        ["dataset_name", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_saved_jobs_dataset_created_at", table_name="saved_jobs")
    op.drop_index(op.f("ix_saved_jobs_id"), table_name="saved_jobs")
    op.drop_table("saved_jobs")
