"""Analytics dashboard for hotel metrics and AI performance."""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from app.core.database.models import Reservation, Message, Guest
from app.core.database.session import get_db
from redis.asyncio import Redis
from sqlalchemy import select, func

from app.core.logging import get_logger
from app.core.memory.vector_store import get_memory_store

logger = get_logger(__name__)


@dataclass
class MetricSnapshot:
    """Point-in-time metric value."""
    timestamp: datetime
    value: float
    metadata: Dict = None


@dataclass
class DashboardMetrics:
    """Complete dashboard metrics."""
    # Business metrics
    occupancy_rate: float
    adr: Decimal  # Average Daily Rate
    revpar: Decimal  # Revenue Per Available Room
    booking_conversion: float

    # AI metrics
    ai_resolution_rate: float
    avg_response_time: float
    sentiment_score: float
    nps_score: Optional[float]

    # Operational metrics
    active_conversations: int
    messages_today: int
    bookings_today: int
    revenue_today: Decimal

    # Trends
    occupancy_trend: List[MetricSnapshot]
    revenue_trend: List[MetricSnapshot]
    ai_usage_trend: List[MetricSnapshot]


class AnalyticsDashboard:
    """Real-time analytics dashboard for hotel operations."""

    def __init__(self):
        """Initialize analytics dashboard."""
        self.redis_client = None
        self.memory_store = None
        self._initialized = False

    async def initialize(self):
        """Initialize connections."""
        if self._initialized:
            return

        try:
            # Get Redis client
            from app.core.config import settings
            self.redis_client = Redis.from_url(settings.redis_url)

            # Get memory store
            self.memory_store = await get_memory_store()

            self._initialized = True
            logger.info("Analytics dashboard initialized")

        except Exception as e:
            logger.error("Failed to initialize dashboard", error=str(e))

    async def get_dashboard_metrics(
            self,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> DashboardMetrics:
        """
        Get complete dashboard metrics.
        
        Args:
            start_date: Start date for metrics (default: today)
            end_date: End date for metrics (default: today)
            
        Returns:
            Dashboard metrics
        """
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = date.today()

        # Gather all metrics concurrently
        results = await asyncio.gather(
            self.get_occupancy_metrics(start_date, end_date),
            self.get_revenue_metrics(start_date, end_date),
            self.get_ai_metrics(start_date, end_date),
            self.get_operational_metrics(),
            self.get_trend_data()
        )

        occupancy_data, revenue_data, ai_data, operational_data, trends = results

        return DashboardMetrics(
            # Business metrics
            occupancy_rate=occupancy_data["occupancy_rate"],
            adr=revenue_data["adr"],
            revpar=revenue_data["revpar"],
            booking_conversion=occupancy_data["conversion_rate"],

            # AI metrics
            ai_resolution_rate=ai_data["resolution_rate"],
            avg_response_time=ai_data["avg_response_time"],
            sentiment_score=ai_data["sentiment_score"],
            nps_score=ai_data.get("nps_score"),

            # Operational metrics
            active_conversations=operational_data["active_conversations"],
            messages_today=operational_data["messages_today"],
            bookings_today=operational_data["bookings_today"],
            revenue_today=operational_data["revenue_today"],

            # Trends
            occupancy_trend=trends["occupancy"],
            revenue_trend=trends["revenue"],
            ai_usage_trend=trends["ai_usage"]
        )

    async def get_occupancy_metrics(
            self,
            start_date: date,
            end_date: date
    ) -> Dict:
        """Calculate occupancy metrics."""
        async with get_db() as db:
            # Total available room nights
            days = (end_date - start_date).days + 1
            total_rooms = 20  # From hotel configuration
            available_room_nights = total_rooms * days

            # Occupied room nights
            result = await db.execute(
                select(func.count(Reservation.id))
                .where(Reservation.check_in <= end_date)
                .where(Reservation.check_out >= start_date)
                .where(Reservation.status.in_(["confirmed", "checked_in"]))
            )
            occupied_nights = result.scalar() or 0

            # Conversion rate
            inquiries_result = await db.execute(
                select(func.count(Message.id.distinct()))
                .where(Message.created_at >= datetime.combine(start_date, datetime.min.time()))
                .where(Message.created_at <= datetime.combine(end_date, datetime.max.time()))
                .where(Message.metadata["intent"].astext == "pricing_request")
            )
            total_inquiries = inquiries_result.scalar() or 0

            bookings_result = await db.execute(
                select(func.count(Reservation.id))
                .where(Reservation.created_at >= datetime.combine(start_date, datetime.min.time()))
                .where(Reservation.created_at <= datetime.combine(end_date, datetime.max.time()))
            )
            total_bookings = bookings_result.scalar() or 0

            return {
                "occupancy_rate": (occupied_nights / available_room_nights * 100) if available_room_nights > 0 else 0,
                "occupied_nights": occupied_nights,
                "available_nights": available_room_nights,
                "conversion_rate": (total_bookings / total_inquiries * 100) if total_inquiries > 0 else 0,
                "total_inquiries": total_inquiries,
                "total_bookings": total_bookings
            }

    async def get_revenue_metrics(
            self,
            start_date: date,
            end_date: date
    ) -> Dict:
        """Calculate revenue metrics."""
        async with get_db() as db:
            # Total revenue
            result = await db.execute(
                select(func.sum(Reservation.total_amount))
                .where(Reservation.check_in >= start_date)
                .where(Reservation.check_in <= end_date)
                .where(Reservation.status.in_(["confirmed", "checked_in", "checked_out"]))
            )
            total_revenue = result.scalar() or Decimal("0")

            # Room nights sold
            nights_result = await db.execute(
                select(func.sum(
                    func.extract('day', Reservation.check_out - Reservation.check_in)
                ))
                .where(Reservation.check_in >= start_date)
                .where(Reservation.check_in <= end_date)
                .where(Reservation.status.in_(["confirmed", "checked_in", "checked_out"]))
            )
            room_nights_sold = nights_result.scalar() or 0

            # Calculate ADR and RevPAR
            days = (end_date - start_date).days + 1
            total_rooms = 20
            available_room_nights = total_rooms * days

            adr = (total_revenue / room_nights_sold) if room_nights_sold > 0 else Decimal("0")
            revpar = (total_revenue / available_room_nights) if available_room_nights > 0 else Decimal("0")

            return {
                "total_revenue": total_revenue,
                "adr": adr,
                "revpar": revpar,
                "room_nights_sold": room_nights_sold
            }

    async def get_ai_metrics(
            self,
            start_date: date,
            end_date: date
    ) -> Dict:
        """Calculate AI performance metrics."""
        async with get_db() as db:
            # Total conversations
            result = await db.execute(
                select(func.count(Message.guest_id.distinct()))
                .where(Message.created_at >= datetime.combine(start_date, datetime.min.time()))
                .where(Message.created_at <= datetime.combine(end_date, datetime.max.time()))
            )
            total_conversations = result.scalar() or 0

            # Conversations transferred to human
            transferred_result = await db.execute(
                select(func.count(Message.guest_id.distinct()))
                .where(Message.created_at >= datetime.combine(start_date, datetime.min.time()))
                .where(Message.created_at <= datetime.combine(end_date, datetime.max.time()))
                .where(Message.metadata["needs_human"].astext == "true")
            )
            transferred_conversations = transferred_result.scalar() or 0

            # Average response time
            response_times = await db.execute(
                select(Message.response_time)
                .where(Message.created_at >= datetime.combine(start_date, datetime.min.time()))
                .where(Message.created_at <= datetime.combine(end_date, datetime.max.time()))
                .where(Message.response_time.isnot(None))
            )

            times = [r[0] for r in response_times]
            avg_response_time = np.mean(times) if times else 0

            # Sentiment analysis
            if self.memory_store:
                sentiment_scores = []

                # Sample recent conversations
                recent_guests = await db.execute(
                    select(Message.guest_id.distinct())
                    .where(Message.created_at >= datetime.now() - timedelta(days=7))
                    .limit(100)
                )

                for guest_id in recent_guests.scalars():
                    profile = await self.memory_store.get_guest_profile(guest_id)
                    if profile["sentiment"] == "positive":
                        sentiment_scores.append(1.0)
                    elif profile["sentiment"] == "neutral":
                        sentiment_scores.append(0.5)
                    else:
                        sentiment_scores.append(0.0)

                sentiment_score = np.mean(sentiment_scores) if sentiment_scores else 0.5
            else:
                sentiment_score = 0.5

            # NPS calculation (if available)
            nps_result = await db.execute(
                select(Guest.metadata["nps_score"])
                .where(Guest.metadata["nps_score"].isnot(None))
                .where(Guest.updated_at >= datetime.now() - timedelta(days=30))
            )

            nps_scores = [int(r[0]) for r in nps_result if r[0]]
            nps_score = self._calculate_nps(nps_scores) if nps_scores else None

            resolution_rate = ((
                                           total_conversations - transferred_conversations) / total_conversations * 100) if total_conversations > 0 else 100

            return {
                "resolution_rate": resolution_rate,
                "avg_response_time": avg_response_time,
                "sentiment_score": sentiment_score,
                "nps_score": nps_score,
                "total_conversations": total_conversations,
                "transferred_conversations": transferred_conversations
            }

    async def get_operational_metrics(self) -> Dict:
        """Get real-time operational metrics."""
        today = date.today()

        # Active conversations (from Redis)
        active_conversations = 0
        if self.redis_client:
            sessions = await self.redis_client.keys("session:*")
            active_conversations = len(sessions)

        async with get_db() as db:
            # Messages today
            messages_result = await db.execute(
                select(func.count(Message.id))
                .where(Message.created_at >= datetime.combine(today, datetime.min.time()))
            )
            messages_today = messages_result.scalar() or 0

            # Bookings today
            bookings_result = await db.execute(
                select(func.count(Reservation.id))
                .where(Reservation.created_at >= datetime.combine(today, datetime.min.time()))
            )
            bookings_today = bookings_result.scalar() or 0

            # Revenue today
            revenue_result = await db.execute(
                select(func.sum(Reservation.total_amount))
                .where(Reservation.created_at >= datetime.combine(today, datetime.min.time()))
            )
            revenue_today = revenue_result.scalar() or Decimal("0")

        return {
            "active_conversations": active_conversations,
            "messages_today": messages_today,
            "bookings_today": bookings_today,
            "revenue_today": revenue_today
        }

    async def get_trend_data(self, days: int = 30) -> Dict:
        """Get trend data for charts."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        trends = {
            "occupancy": [],
            "revenue": [],
            "ai_usage": []
        }

        # Generate daily metrics
        current_date = start_date
        while current_date <= end_date:
            # Get metrics for this day
            occupancy = await self.get_occupancy_metrics(current_date, current_date)
            revenue = await self.get_revenue_metrics(current_date, current_date)
            ai = await self.get_ai_metrics(current_date, current_date)

            # Add to trends
            timestamp = datetime.combine(current_date, datetime.min.time())

            trends["occupancy"].append(MetricSnapshot(
                timestamp=timestamp,
                value=occupancy["occupancy_rate"],
                metadata={"bookings": occupancy["total_bookings"]}
            ))

            trends["revenue"].append(MetricSnapshot(
                timestamp=timestamp,
                value=float(revenue["total_revenue"]),
                metadata={"adr": float(revenue["adr"])}
            ))

            trends["ai_usage"].append(MetricSnapshot(
                timestamp=timestamp,
                value=ai["total_conversations"],
                metadata={"resolution_rate": ai["resolution_rate"]}
            ))

            current_date += timedelta(days=1)

        return trends

    def _calculate_nps(self, scores: List[int]) -> float:
        """Calculate Net Promoter Score."""
        if not scores:
            return 0.0

        promoters = sum(1 for s in scores if s >= 9)
        detractors = sum(1 for s in scores if s <= 6)
        total = len(scores)

        nps = ((promoters - detractors) / total) * 100
        return nps

    async def get_guest_insights(self, limit: int = 10) -> List[Dict]:
        """Get insights about top guests."""
        if not self.memory_store:
            return []

        insights = []

        async with get_db() as db:
            # Get top guests by booking value
            result = await db.execute(
                select(
                    Reservation.guest_id,
                    func.count(Reservation.id).label("total_bookings"),
                    func.sum(Reservation.total_amount).label("total_spent")
                )
                .group_by(Reservation.guest_id)
                .order_by(func.sum(Reservation.total_amount).desc())
                .limit(limit)
            )

            for row in result:
                guest_id, total_bookings, total_spent = row

                # Get guest profile
                profile = await self.memory_store.get_guest_profile(guest_id)

                # Get guest info
                guest_result = await db.execute(
                    select(Guest).where(Guest.id == guest_id)
                )
                guest = guest_result.scalar_one_or_none()

                if guest:
                    insights.append({
                        "guest_id": guest_id,
                        "name": guest.name,
                        "total_bookings": total_bookings,
                        "total_spent": float(total_spent),
                        "preferences": profile["preferences"],
                        "sentiment": profile["sentiment"],
                        "repeat_guest": profile["patterns"]["repeat_guest"],
                        "topics": profile["topics"][:3]  # Top 3 topics
                    })

        return insights

    async def get_performance_alerts(self) -> List[Dict]:
        """Get performance alerts and anomalies."""
        alerts = []
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Get today's metrics
        today_metrics = await self.get_dashboard_metrics(today, today)

        # Get yesterday's metrics for comparison
        yesterday_metrics = await self.get_dashboard_metrics(yesterday, yesterday)

        # Check occupancy drop
        if today_metrics.occupancy_rate < yesterday_metrics.occupancy_rate * 0.8:
            alerts.append({
                "type": "warning",
                "category": "occupancy",
                "message": f"Occupancy dropped {yesterday_metrics.occupancy_rate - today_metrics.occupancy_rate:.1f}% from yesterday",
                "value": today_metrics.occupancy_rate,
                "previous_value": yesterday_metrics.occupancy_rate
            })

        # Check AI resolution rate
        if today_metrics.ai_resolution_rate < 70:
            alerts.append({
                "type": "critical",
                "category": "ai_performance",
                "message": f"AI resolution rate is low at {today_metrics.ai_resolution_rate:.1f}%",
                "value": today_metrics.ai_resolution_rate,
                "threshold": 70
            })

        # Check response time
        if today_metrics.avg_response_time > 5:
            alerts.append({
                "type": "warning",
                "category": "response_time",
                "message": f"Average response time is high at {today_metrics.avg_response_time:.1f}s",
                "value": today_metrics.avg_response_time,
                "threshold": 5
            })

        # Check sentiment
        if today_metrics.sentiment_score < 0.4:
            alerts.append({
                "type": "critical",
                "category": "sentiment",
                "message": "Guest sentiment is negative",
                "value": today_metrics.sentiment_score,
                "threshold": 0.4
            })

        return alerts

    async def generate_daily_report(self) -> Dict:
        """Generate comprehensive daily report."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)

        # Get metrics for different periods
        today_metrics = await self.get_dashboard_metrics(today, today)
        yesterday_metrics = await self.get_dashboard_metrics(yesterday, yesterday)
        week_metrics = await self.get_dashboard_metrics(last_week, today)
        month_metrics = await self.get_dashboard_metrics(last_month, today)

        # Get insights and alerts
        guest_insights = await self.get_guest_insights(5)
        alerts = await self.get_performance_alerts()

        report = {
            "date": today.isoformat(),
            "summary": {
                "occupancy_rate": today_metrics.occupancy_rate,
                "revenue_today": float(today_metrics.revenue_today),
                "bookings_today": today_metrics.bookings_today,
                "ai_resolution_rate": today_metrics.ai_resolution_rate
            },
            "comparisons": {
                "vs_yesterday": {
                    "occupancy_change": today_metrics.occupancy_rate - yesterday_metrics.occupancy_rate,
                    "revenue_change": float(today_metrics.revenue_today - yesterday_metrics.revenue_today),
                    "bookings_change": today_metrics.bookings_today - yesterday_metrics.bookings_today
                },
                "week_avg": {
                    "occupancy": week_metrics.occupancy_rate,
                    "adr": float(week_metrics.adr),
                    "revpar": float(week_metrics.revpar)
                },
                "month_avg": {
                    "occupancy": month_metrics.occupancy_rate,
                    "adr": float(month_metrics.adr),
                    "revpar": float(month_metrics.revpar)
                }
            },
            "ai_performance": {
                "total_conversations": today_metrics.messages_today,
                "resolution_rate": today_metrics.ai_resolution_rate,
                "avg_response_time": today_metrics.avg_response_time,
                "sentiment_score": today_metrics.sentiment_score
            },
            "top_guests": guest_insights,
            "alerts": alerts,
            "recommendations": self._generate_recommendations(today_metrics, alerts)
        }

        return report

    def _generate_recommendations(
            self,
            metrics: DashboardMetrics,
            alerts: List[Dict]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Low occupancy
        if metrics.occupancy_rate < 60:
            recommendations.append(
                "Consider running a promotional campaign to boost occupancy. "
                "Target previous guests with special offers."
            )

        # Low conversion
        if metrics.booking_conversion < 15:
            recommendations.append(
                "Review pricing strategy and response templates. "
                "Consider A/B testing different messaging approaches."
            )

        # AI performance
        if metrics.ai_resolution_rate < 75:
            recommendations.append(
                "Review recent conversations to identify patterns in transfers. "
                "Consider training the AI on new scenarios."
            )

        # Sentiment issues
        if metrics.sentiment_score < 0.5:
            recommendations.append(
                "Investigate negative sentiment causes. "
                "Proactively reach out to dissatisfied guests."
            )

        # Revenue optimization
        if float(metrics.adr) < 280:
            recommendations.append(
                "Room rates are below average. Consider dynamic pricing "
                "based on demand and competitor analysis."
            )

        return recommendations


# API endpoints for dashboard
from fastapi import APIRouter, Query
from datetime import date as date_type

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(
        start_date: Optional[date_type] = Query(None),
        end_date: Optional[date_type] = Query(None)
):
    """Get dashboard metrics."""
    dashboard = AnalyticsDashboard()
    await dashboard.initialize()

    metrics = await dashboard.get_dashboard_metrics(start_date, end_date)

    return {
        "metrics": metrics,
        "generated_at": datetime.now().isoformat()
    }


@router.get("/report/daily")
async def get_daily_report():
    """Get daily report."""
    dashboard = AnalyticsDashboard()
    await dashboard.initialize()

    report = await dashboard.generate_daily_report()
    return report


@router.get("/alerts")
async def get_alerts():
    """Get current alerts."""
    dashboard = AnalyticsDashboard()
    await dashboard.initialize()

    alerts = await dashboard.get_performance_alerts()
    return {"alerts": alerts}


@router.get("/insights/guests")
async def get_guest_insights(limit: int = Query(10, ge=1, le=50)):
    """Get guest insights."""
    dashboard = AnalyticsDashboard()
    await dashboard.initialize()

    insights = await dashboard.get_guest_insights(limit)
    return {"guests": insights}
