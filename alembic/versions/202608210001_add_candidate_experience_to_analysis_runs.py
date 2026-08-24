"""add candidate experience to analysis runs

Revision ID: 202608210001
Revises: 202608200001
Create Date: 2026-08-21 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202608210001"
down_revision = "202608200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "candidate_experience",
            sa.String(length=100),
            nullable=False,
            server_default="Not specified",
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "candidate_experience")
