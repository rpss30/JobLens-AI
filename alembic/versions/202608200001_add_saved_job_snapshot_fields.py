"""add saved job snapshot fields

Revision ID: 202608200001
Revises: 202608190001
Create Date: 2026-08-20 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202608200001"
down_revision = "202608190001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Copy in the rest of what a saved posting needs to be listed.

    The list a save appears in shows the date and filters on the experience
    level. Without these a save whose posting has left the dataset could
    still be held but not shown beside the ones that remain.

    The company mark is not among them: it is derived from the company and
    the source url, both of which are already copied in.
    """
    for column in (
        sa.Column(
            "date_posted",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "experience_level",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
    ):
        op.add_column("saved_jobs", column)


def downgrade() -> None:
    for name in ("experience_level", "date_posted"):
        op.drop_column("saved_jobs", name)
