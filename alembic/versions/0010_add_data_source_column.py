"""Add data_source column to track FBref vs RapidAPI data

Revision ID: 0010_add_data_source
Revises: e82effb2c988
Create Date: 2026-02-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010_add_data_source'
down_revision: Union[str, Sequence[str], None] = 'e82effb2c988'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add data_source column to players table
    op.add_column('players',
                  sa.Column('data_source',
                            sa.String(),
                            nullable=False,
                            server_default='fbref'))
    op.create_index(op.f('ix_players_data_source'),
                    'players',
                    ['data_source'],
                    unique=False)

    # Add data_source column to competition_stats table
    op.add_column('competition_stats',
                  sa.Column('data_source',
                            sa.String(),
                            nullable=False,
                            server_default='fbref'))
    op.create_index(op.f('ix_competition_stats_data_source'),
                    'competition_stats',
                    ['data_source'],
                    unique=False)

    # Add data_source column to goalkeeper_stats table
    op.add_column('goalkeeper_stats',
                  sa.Column('data_source',
                            sa.String(),
                            nullable=False,
                            server_default='fbref'))
    op.create_index(op.f('ix_goalkeeper_stats_data_source'),
                    'goalkeeper_stats',
                    ['data_source'],
                    unique=False)

    # Add data_source column to player_matches table
    op.add_column('player_matches',
                  sa.Column('data_source',
                            sa.String(),
                            nullable=False,
                            server_default='fbref'))
    op.create_index(op.f('ix_player_matches_data_source'),
                    'player_matches',
                    ['data_source'],
                    unique=False)

    # Add data_source column to lineup_cache table
    op.add_column('lineup_cache',
                  sa.Column('data_source',
                            sa.String(),
                            nullable=False,
                            server_default='fbref'))
    op.create_index(op.f('ix_lineup_cache_data_source'),
                    'lineup_cache',
                    ['data_source'],
                    unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove data_source from lineup_cache
    op.drop_index(op.f('ix_lineup_cache_data_source'),
                  table_name='lineup_cache')
    op.drop_column('lineup_cache', 'data_source')

    # Remove data_source from player_matches
    op.drop_index(op.f('ix_player_matches_data_source'),
                  table_name='player_matches')
    op.drop_column('player_matches', 'data_source')

    # Remove data_source from goalkeeper_stats
    op.drop_index(op.f('ix_goalkeeper_stats_data_source'),
                  table_name='goalkeeper_stats')
    op.drop_column('goalkeeper_stats', 'data_source')

    # Remove data_source from competition_stats
    op.drop_index(op.f('ix_competition_stats_data_source'),
                  table_name='competition_stats')
    op.drop_column('competition_stats', 'data_source')

    # Remove data_source from players
    op.drop_index(op.f('ix_players_data_source'),
                  table_name='players')
    op.drop_column('players', 'data_source')
