from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class PlayerSeasonStats(Base):
    """Statystyki gracza dla konkretnego sezonu - rozszerzone o wszystkie dane z RapidAPI"""
    __tablename__ = "player_season_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    season = Column(Integer, nullable=False, index=True)  # Rok rozpoczęcia sezonu (np. 2024 dla 2024/2025)
    
    # ==================== PODSTAWOWE (już masz) ====================
    matches = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    starts = Column(Integer, nullable=True)
    
    # Expected metrics
    xG = Column(Float, nullable=True)  # Expected Goals
    xA = Column(Float, nullable=True)  # Expected Assists
    
    # Informacje klubowe
    team = Column(String, nullable=True)
    league = Column(String, nullable=True)
    
    # ==================== NOWE: STRZAŁY (Shooting) ====================
    shots_total = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    shots_on_target_pct = Column(Float, nullable=True)
    goals_per_shot = Column(Float, nullable=True)
    goals_per_shot_on_target = Column(Float, nullable=True)
    average_shot_distance = Column(Float, nullable=True)
    free_kick_shots = Column(Integer, default=0)
    penalty_kicks_made = Column(Integer, default=0)
    penalty_kicks_attempted = Column(Integer, default=0)
    xg_net = Column(Float, nullable=True)  # npxG (non-penalty xG)
    npxg_per_shot = Column(Float, nullable=True)
    
    # ==================== NOWE: PODANIA (Passing) ====================
    passes_completed = Column(Integer, default=0)
    passes_attempted = Column(Integer, default=0)
    pass_completion_pct = Column(Float, nullable=True)
    total_passing_distance = Column(Integer, default=0)
    progressive_passing_distance = Column(Integer, default=0)
    
    # Podania krótkie/średnie/długie
    short_passes_completed = Column(Integer, default=0)
    short_passes_attempted = Column(Integer, default=0)
    medium_passes_completed = Column(Integer, default=0)
    medium_passes_attempted = Column(Integer, default=0)
    long_passes_completed = Column(Integer, default=0)
    long_passes_attempted = Column(Integer, default=0)
    
    # Kluczowe podania
    key_passes = Column(Integer, default=0)
    passes_into_final_third = Column(Integer, default=0)
    passes_into_penalty_area = Column(Integer, default=0)
    crosses_into_penalty_area = Column(Integer, default=0)
    progressive_passes = Column(Integer, default=0)  # Już było, ale dobrze mieć
    
    # ==================== NOWE: TYPY PODAŃ (Pass Types) ====================
    live_ball_passes = Column(Integer, default=0)
    dead_ball_passes = Column(Integer, default=0)
    free_kick_passes = Column(Integer, default=0)
    through_balls = Column(Integer, default=0)
    switches = Column(Integer, default=0)
    crosses = Column(Integer, default=0)
    throw_ins = Column(Integer, default=0)
    corner_kicks = Column(Integer, default=0)
    inswinging_corners = Column(Integer, default=0)
    outswinging_corners = Column(Integer, default=0)
    straight_corners = Column(Integer, default=0)
    passes_offside = Column(Integer, default=0)
    passes_blocked = Column(Integer, default=0)
    
    # ==================== NOWE: TWORZENIE AKCJI (GCA) ====================
    shot_creating_actions = Column(Integer, default=0)  # SCA
    sca_live_pass = Column(Integer, default=0)
    sca_dead_ball = Column(Integer, default=0)
    sca_dribble = Column(Integer, default=0)
    sca_shot = Column(Integer, default=0)
    sca_foul_drawn = Column(Integer, default=0)
    sca_defensive_action = Column(Integer, default=0)
    
    goal_creating_actions = Column(Integer, default=0)  # GCA
    gca_live_pass = Column(Integer, default=0)
    gca_dead_ball = Column(Integer, default=0)
    gca_dribble = Column(Integer, default=0)
    gca_shot = Column(Integer, default=0)
    gca_foul_drawn = Column(Integer, default=0)
    gca_defensive_action = Column(Integer, default=0)
    
    # ==================== NOWE: OBRONA (Defense) ====================
    tackles = Column(Integer, default=0)
    tackles_won = Column(Integer, default=0)
    tackles_def_third = Column(Integer, default=0)
    tackles_mid_third = Column(Integer, default=0)
    tackles_att_third = Column(Integer, default=0)
    
    dribble_tackles = Column(Integer, default=0)
    dribbles_vs_tackles = Column(Integer, default=0)
    dribbled_past = Column(Integer, default=0)
    
    blocks = Column(Integer, default=0)
    shots_blocked = Column(Integer, default=0)
    pass_blocks = Column(Integer, default=0)
    
    interceptions = Column(Integer, default=0)
    clearances = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    
    # ==================== NOWE: POSIADANIE (Possession) ====================
    touches = Column(Integer, default=0)
    touches_def_pen_area = Column(Integer, default=0)
    touches_def_third = Column(Integer, default=0)
    touches_mid_third = Column(Integer, default=0)
    touches_att_third = Column(Integer, default=0)
    touches_att_pen_area = Column(Integer, default=0)
    touches_live_ball = Column(Integer, default=0)
    
    # Dryblingi
    dribbles_completed = Column(Integer, default=0)
    dribbles_attempted = Column(Integer, default=0)
    dribble_success_pct = Column(Float, nullable=True)
    players_dribbled_past = Column(Integer, default=0)
    nutmegs = Column(Integer, default=0)
    
    # Noszenie piłki
    carries = Column(Integer, default=0)
    total_carrying_distance = Column(Integer, default=0)
    progressive_carrying_distance = Column(Integer, default=0)
    progressive_carries = Column(Integer, default=0)  # Już było
    carries_into_final_third = Column(Integer, default=0)
    carries_into_penalty_area = Column(Integer, default=0)
    
    # Kontrola
    miscontrols = Column(Integer, default=0)
    dispossessed = Column(Integer, default=0)
    passes_received = Column(Integer, default=0)
    progressive_passes_received = Column(Integer, default=0)
    
    # ==================== NOWE: CZAS GRY (Playing Time) ====================
    minutes_per_match = Column(Float, nullable=True)
    minutes_pct = Column(Float, nullable=True)  # % dostępnych minut
    minutes_per_start = Column(Float, nullable=True)
    complete_matches = Column(Integer, default=0)  # Pełne 90 minut
    substitutions_on = Column(Integer, default=0)
    substitutions_off = Column(Integer, default=0)
    unused_substitute = Column(Integer, default=0)
    points_per_match = Column(Float, nullable=True)
    on_goals_for = Column(Integer, default=0)
    on_goals_against = Column(Integer, default=0)
    plus_minus = Column(Integer, default=0)
    plus_minus_per_90 = Column(Float, nullable=True)
    on_xg_for = Column(Float, nullable=True)
    on_xg_against = Column(Float, nullable=True)
    xg_plus_minus = Column(Float, nullable=True)
    xg_plus_minus_per_90 = Column(Float, nullable=True)
    
    # ==================== NOWE: RÓŻNE (Miscellaneous) ====================
    fouls_committed = Column(Integer, default=0)
    fouls_drawn = Column(Integer, default=0)
    offsides = Column(Integer, default=0)
    penalty_kicks_won = Column(Integer, default=0)
    penalty_kicks_conceded = Column(Integer, default=0)
    own_goals = Column(Integer, default=0)
    ball_recoveries = Column(Integer, default=0)
    
    # Pojedynki powietrzne
    aerials_won = Column(Integer, default=0)
    aerials_lost = Column(Integer, default=0)
    aerials_won_pct = Column(Float, nullable=True)
    
    # ==================== RELACJA ====================
    player = relationship("Player", back_populates="season_stats")
    
    def __repr__(self):
        return f"<PlayerSeasonStats(player_id={self.player_id}, season={self.season}, goals={self.goals})>"

