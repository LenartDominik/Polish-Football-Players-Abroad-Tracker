"""
API Usage Metrics Model for Rate Limiting

Tracks API usage for quota management and alerting.
"""
from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.orm import relationship
from ..database import Base


class ApiUsageMetrics(Base):
    """
    API usage tracking for rate limiting

    Tracks:
    - Daily usage (date column)
    - Monthly usage (month column in format YYYY-MM)
    - Per-endpoint usage
    - Status codes for error tracking
    """
    __tablename__ = "api_usage_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)  # Format: 2026-02
    requests_count = Column(Integer, default=0, nullable=False)
    endpoint = Column(String(100), nullable=True)
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<ApiUsageMetrics date={self.date} endpoint={self.endpoint} count={self.requests_count}>"
