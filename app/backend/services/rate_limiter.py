"""
Rate Limiter and Quota Monitor for RapidAPI

Monitors API usage and provides alerts when approaching quota limits.

Features:
- Track daily/monthly API usage
- Alert at 80% daily, 90% monthly quota
- Prevent API limit overages
- Store usage metrics in database

RapidAPI Free Tier limits:
- 100 requests/month
"""
import logging
from typing import Optional, Dict
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.backend.models.api_usage_metrics import ApiUsageMetrics

logger = logging.getLogger(__name__)


# API Quota settings (RapidAPI Free Tier)
# Can be overridden with environment variables
import os
MONTHLY_QUOTA = int(os.getenv("RAPIDAPI_MONTHLY_QUOTA", "100"))
DAILY_QUOTA = int(os.getenv("RAPIDAPI_DAILY_QUOTA", "10"))  # Conservative: ~10/day stays under 100/month

# Alert thresholds
DAILY_WARNING_THRESHOLD = 0.8  # 80% of daily quota
MONTHLY_WARNING_THRESHOLD = 0.8  # 80% of monthly quota
MONTHLY_CRITICAL_THRESHOLD = 0.9  # 90% of monthly quota


class RateLimiter:
    """Rate limiter and quota monitor for API usage"""

    def __init__(self, db: Session, monthly_quota: int = MONTHLY_QUOTA, daily_quota: int = DAILY_QUOTA):
        """
        Initialize rate limiter

        Args:
            db: Database session
            monthly_quota: Monthly request limit
            daily_quota: Daily request limit (soft limit)
        """
        self.db = db
        self.monthly_quota = monthly_quota
        self.daily_quota = daily_quota
        self.session_requests = 0  # Track requests in current session

    def record_request(
        self,
        endpoint: str,
        status_code: Optional[int] = None
    ) -> bool:
        """
        Record an API request in the metrics

        Args:
            endpoint: API endpoint called
            status_code: HTTP status code (optional)

        Returns:
            True if recorded successfully
        """
        today = date.today()
        month_str = today.strftime("%Y-%m")

        try:
            metric = ApiUsageMetrics(
                date=today,
                month=month_str,
                requests_count=1,
                endpoint=endpoint,
                status_code=status_code,
                created_at=datetime.now()
            )
            self.db.add(metric)
            self.db.commit()

            self.session_requests += 1

            logger.debug(f"Recorded API request: {endpoint} (status: {status_code})")

            # Check if we should send alerts
            self._check_and_alert()

            return True

        except Exception as e:
            logger.error(f"Failed to record API request: {e}")
            self.db.rollback()
            return False

    async def record_request_async(
        self,
        endpoint: str,
        status_code: Optional[int] = None
    ) -> bool:
        """
        Record an API request asynchronously in the metrics.

        Uses run_in_executor to avoid blocking the event loop with DB commits.

        Args:
            endpoint: API endpoint called
            status_code: HTTP status code (optional)

        Returns:
            True if recorded successfully
        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool,
                self.record_request,
                endpoint,
                status_code
            )

    def get_daily_usage(self, day: Optional[date] = None) -> Dict:
        """
        Get daily usage statistics

        Args:
            day: Date to check (uses today if None)

        Returns:
            Dict with daily usage info
        """
        if day is None:
            day = date.today()

        result = self.db.query(
            func.sum(ApiUsageMetrics.requests_count)
        ).filter(
            ApiUsageMetrics.date == day
        ).scalar()

        count = result or 0
        percentage = (count / self.daily_quota * 100) if self.daily_quota > 0 else 0

        return {
            "date": str(day),
            "requests": count,
            "quota": self.daily_quota,
            "percentage": round(percentage, 2),
            "remaining": max(0, self.daily_quota - count)
        }

    def get_monthly_usage(self, month: Optional[str] = None) -> Dict:
        """
        Get monthly usage statistics

        Args:
            month: Month string in YYYY-MM format (uses current month if None)

        Returns:
            Dict with monthly usage info
        """
        if month is None:
            month = date.today().strftime("%Y-%m")

        result = self.db.query(
            func.sum(ApiUsageMetrics.requests_count)
        ).filter(
            ApiUsageMetrics.month == month
        ).scalar()

        count = result or 0
        percentage = (count / self.monthly_quota * 100) if self.monthly_quota > 0 else 0

        return {
            "month": month,
            "requests": count,
            "quota": self.monthly_quota,
            "percentage": round(percentage, 2),
            "remaining": max(0, self.monthly_quota - count)
        }

    def get_usage_by_endpoint(self, month: Optional[str] = None) -> Dict[str, int]:
        """
        Get usage breakdown by endpoint

        Args:
            month: Month string (uses current month if None)

        Returns:
            Dict mapping endpoint -> request count
        """
        if month is None:
            month = date.today().strftime("%Y-%m")

        results = self.db.query(
            ApiUsageMetrics.endpoint,
            func.sum(ApiUsageMetrics.requests_count)
        ).filter(
            ApiUsageMetrics.month == month
        ).group_by(
            ApiUsageMetrics.endpoint
        ).all()

        return {endpoint or "unknown": count for endpoint, count in results}

    def can_make_request(self) -> tuple[bool, str]:
        """
        Check if we can make another request without exceeding quota

        Returns:
            (can_make, reason) tuple
        """
        daily = self.get_daily_usage()
        monthly = self.get_monthly_usage()

        # Hard limit: monthly quota
        if monthly["requests"] >= self.monthly_quota:
            return False, f"Monthly quota exceeded: {monthly['requests']}/{self.monthly_quota}"

        # Warning threshold: monthly
        if monthly["percentage"] >= MONTHLY_CRITICAL_THRESHOLD * 100:
            return False, f"Monthly quota nearly exhausted: {monthly['percentage']}%"

        # Soft limit: daily quota (can be exceeded in emergencies)
        if daily["requests"] >= self.daily_quota:
            logger.warning(f"Daily quota exceeded: {daily['requests']}/{self.daily_quota}")
            return True, "Daily quota exceeded but monthly quota allows more"

        return True, "OK"

    def _check_and_alert(self):
        """Check usage and log alerts if thresholds exceeded"""
        daily = self.get_daily_usage()
        monthly = self.get_monthly_usage()

        # Daily warning
        if daily["percentage"] >= DAILY_WARNING_THRESHOLD * 100:
            logger.warning(
                f"⚠️ DAILY QUOTA WARNING: {daily['requests']}/{self.daily_quota} "
                f"({daily['percentage']}%) requests used today"
            )

        # Monthly warning
        if monthly["percentage"] >= MONTHLY_WARNING_THRESHOLD * 100:
            logger.warning(
                f"⚠️ MONTHLY QUOTA WARNING: {monthly['requests']}/{self.monthly_quota} "
                f"({monthly['percentage']}%) requests used this month"
            )

        # Monthly critical
        if monthly["percentage"] >= MONTHLY_CRITICAL_THRESHOLD * 100:
            logger.error(
                f"🚨 MONTHLY QUOTA CRITICAL: {monthly['requests']}/{self.monthly_quota} "
                f"({monthly['percentage']}%) requests used this month"
                )

    def get_full_report(self) -> Dict:
        """
        Get comprehensive usage report

        Returns:
            Dict with all usage statistics
        """
        daily = self.get_daily_usage()
        monthly = self.get_monthly_usage()
        by_endpoint = self.get_usage_by_endpoint()

        return {
            "daily": daily,
            "monthly": monthly,
            "by_endpoint": by_endpoint,
            "session_requests": self.session_requests,
            "settings": {
                "monthly_quota": self.monthly_quota,
                "daily_quota": self.daily_quota,
                "warning_threshold": int(MONTHLY_WARNING_THRESHOLD * 100),
                "critical_threshold": int(MONTHLY_CRITICAL_THRESHOLD * 100)
            }
        }

    def cleanup_old_metrics(self, days_to_keep: int = 90):
        """
        Remove old metrics to keep database size manageable

        Args:
            days_to_keep: Number of days of history to keep
        """
        from datetime import timedelta

        cutoff_date = date.today() - timedelta(days=days_to_keep)

        deleted = self.db.query(ApiUsageMetrics).filter(
            ApiUsageMetrics.date < cutoff_date
        ).delete()

        self.db.commit()

        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} old API usage metrics entries")


class RateLimitedRapidAPIClient:
    """
    Wrapper for RapidAPIClient with automatic rate limiting

    Automatically records API calls and checks quota before requests.
    """

    def __init__(self, db: Session, rapidapi_client):
        """
        Initialize rate-limited client

        Args:
            db: Database session
            rapidapi_client: RapidAPIClient instance to wrap
        """
        self.db = db
        self.client = rapidapi_client
        self.rate_limiter = RateLimiter(db)

    async def _request(self, endpoint: str, params: dict = None, method_name: str = "request"):
        """
        Make API request with rate limiting

        Args:
            endpoint: API endpoint
            params: Query parameters
            method_name: Name of the API method being called

        Returns:
            API response or None if rate limited
        """
        # Check if we can make request
        can_make, reason = self.rate_limiter.can_make_request()

        if not can_make:
            logger.error(f"❌ Rate limited: {reason}")
            return None

        # Make the request
        response = await self.client._request(endpoint, params)

        # Record the request
        status_code = None
        if response:
            # Success - record with 200 status
            status_code = 200
        else:
            # Failed - record with error status
            status_code = 500

        self.rate_limiter.record_request(
            endpoint=method_name,
            status_code=status_code
        )

        return response

    # Delegate all other methods to underlying client
    def __getattr__(self, name):
        """Delegate undefined attributes to wrapped client"""
        attr = getattr(self.client, name)

        if callable(attr):
            # Wrap async methods with rate limiting
            import inspect
            if inspect.iscoroutinefunction(attr):
                async def wrapped(*args, **kwargs):
                    return await self._request(
                        kwargs.get('endpoint', ''),
                        kwargs.get('params'),
                        name
                    )
                return wrapped

        return attr

    def get_usage_report(self) -> Dict:
        """Get usage report from rate limiter"""
        return self.rate_limiter.get_full_report()
