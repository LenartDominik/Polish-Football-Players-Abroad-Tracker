"""Add cache_store table for enhanced caching

Revision ID: 0020_add_cache_store
Revises: 0010_add_data_source
Create Date: 2026-02-16 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0020_add_cache_store'
down_revision: Union[str, Sequence[str], None] = '0010_add_data_source'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('cache_store',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cache_key', sa.String(length=500), nullable=False),
    sa.Column('cache_type', sa.String(length=50), nullable=False),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False, index=True),
    sa.Column('hits', sa.Integer(), default=0),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cache_key', name='uq_cache_key')
    )
    op.create_index(op.f('ix_cache_store_cache_type'), 'cache_store', ['cache_type'], unique=False)
    op.create_index(op.f('ix_cache_store_id'), 'cache_store', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_cache_store_id'), table_name='cache_store')
    op.drop_index(op.f('ix_cache_store_cache_type'), table_name='cache_store')
    op.drop_table('cache_store')
