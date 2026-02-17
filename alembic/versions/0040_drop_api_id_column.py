"""drop api_id column

Revision ID: 0040_drop_api_id_column
Revises: 0030_add_api_usage_metrics
Create Date: 2025-02-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0040_drop_api_id_column'
down_revision = '0030_add_api_usage_metrics'
branch_labels = None
depends_on = None


def upgrade():
    """Drop the legacy api_id column from players table."""
    op.drop_column('players', 'api_id')


def downgrade():
    """Re-add the api_id column for rollback support."""
    op.add_column('players', sa.Column('api_id', sa.String(), nullable=True))
