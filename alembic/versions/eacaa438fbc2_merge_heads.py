"""merge heads

Revision ID: eacaa438fbc2
Revises: add_npxg_penalty, add_uq_player_match
Create Date: 2025-12-19 02:58:35.423724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eacaa438fbc2'
down_revision: Union[str, Sequence[str], None] = ('add_npxg_penalty', 'add_uq_player_match')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
