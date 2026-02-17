"""Add api_usage_metrics table for rate limiting

Revision ID: 0030_add_api_usage_metrics
Revises: 0020_add_cache_store
Create Date: 2026-02-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0030_add_api_usage_metrics'
down_revision: Union[str, Sequence[str], None] = '0020_add_cache_store'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('api_usage_metrics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False, index=True),
    sa.Column('month', sa.String(length=7), nullable=False, index=True),  # Format: 2026-02
    sa.Column('requests_count', sa.Integer(), default=0, nullable=False),
    sa.Column('endpoint', sa.String(length=100), nullable=True),
    sa.Column('status_code', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('api_usage_metrics')
