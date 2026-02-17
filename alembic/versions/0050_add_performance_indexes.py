"""add performance indexes

Revision ID: 0050_add_performance_indexes
Revises: 0040_drop_api_id_column
Create Date: 2025-02-16

This migration adds compound indexes to improve query performance:
- Players table: team+league, position+league, rapidapi IDs
- Player matches: player+date+competition
- Competition stats: player+season+data_source
- Goalkeeper stats: player+season+data_source

These indexes optimize common query patterns and reduce N+1 queries.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0050_add_performance_indexes'
down_revision = '0040_drop_api_id_column'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance-optimized compound indexes."""

    # Players table indexes
    # Compound index for filtering by team and league (common in live match tracking)
    op.create_index(
        'ix_players_team_league',
        'players',
        ['team', 'league']
    )

    # Compound index for filtering by position and league (useful for leaderboards)
    op.create_index(
        'ix_players_position_league',
        'players',
        ['position', 'league']
    )

    # Compound index for RapidAPI ID lookups (used during sync)
    op.create_index(
        'ix_players_rapidapi_team_player',
        'players',
        ['rapidapi_team_id', 'rapidapi_player_id']
    )

    # Player matches table index
    # Compound index for match logs queries (player + date + competition)
    op.create_index(
        'ix_player_matches_player_date_comp',
        'player_matches',
        ['player_id', 'match_date', 'competition']
    )

    # Competition stats table index
    # Compound index for filtering stats by player, season, and data source
    op.create_index(
        'ix_competition_stats_player_season_datasource',
        'competition_stats',
        ['player_id', 'season', 'data_source']
    )

    # Goalkeeper stats table index
    # Compound index for filtering stats by player, season, and data source
    op.create_index(
        'ix_goalkeeper_stats_player_season_datasource',
        'goalkeeper_stats',
        ['player_id', 'season', 'data_source']
    )


def downgrade():
    """Remove performance indexes for rollback support."""

    # Drop indexes in reverse order of creation
    op.drop_index('ix_goalkeeper_stats_player_season_datasource', table_name='goalkeeper_stats')
    op.drop_index('ix_competition_stats_player_season_datasource', table_name='competition_stats')
    op.drop_index('ix_player_matches_player_date_comp', table_name='player_matches')
    op.drop_index('ix_players_rapidapi_team_player', table_name='players')
    op.drop_index('ix_players_position_league', table_name='players')
    op.drop_index('ix_players_team_league', table_name='players')
