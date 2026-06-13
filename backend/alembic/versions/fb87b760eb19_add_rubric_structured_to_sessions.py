"""add rubric_structured to grading_sessions

Revision ID: fb87b760eb19
Revises: d65d6e156417
Create Date: 2026-06-13 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fb87b760eb19'
down_revision: str | Sequence[str] | None = 'd65d6e156417'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'grading_sessions',
        sa.Column('rubric_structured', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('grading_sessions', 'rubric_structured')
