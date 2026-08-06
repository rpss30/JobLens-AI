"""add ingestion run metadata

Revision ID: 202608050001
Revises: 202607010002
Create Date: 2026-08-05 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202608050001"
down_revision = "202607010002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs",
        sa.Column(
            "run_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("ingestion_runs", "run_metadata", server_default=None)


def downgrade() -> None:
    op.drop_column("ingestion_runs", "run_metadata")
