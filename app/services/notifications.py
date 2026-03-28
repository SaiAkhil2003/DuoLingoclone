from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from app.extensions import db
from app.models.core import Notification, User, utcnow


def schedule_notification(
    user: User,
    notification_type: str,
    title: str,
    message: str,
    scheduled_for: datetime,
    payload: dict | None = None,
) -> Notification:
    existing = Notification.query.filter_by(
        user_id=user.id,
        notification_type=notification_type,
        scheduled_for=scheduled_for,
    ).first()
    if existing:
        return existing
    notification = Notification(
        user_id=user.id,
        notification_type=notification_type,
        title=title,
        message=message,
        scheduled_for=scheduled_for,
        payload=payload or {},
    )
    db.session.add(notification)
    db.session.flush()
    return notification


def refresh_notifications(user: User) -> list[Notification]:
    now = utcnow()
    reminder_hour, reminder_minute = [int(part) for part in user.preferred_reminder_time.split(":")]
    reminder_time = datetime.combine(date.today(), time(reminder_hour, reminder_minute), tzinfo=timezone.utc)
    streak_alert_time = datetime.combine(date.today(), time(21, 0), tzinfo=timezone.utc)
    boost_alert_time = datetime.combine(date.today(), time(10, 0), tzinfo=timezone.utc)

    if user.last_active_date != date.today():
        schedule_notification(
            user,
            "daily_reminder",
            "Time to learn",
            "Your next lesson is ready. Keep the streak alive today.",
            reminder_time if reminder_time > now else reminder_time + timedelta(days=1),
        )

    if user.last_active_date == date.today() - timedelta(days=1):
        schedule_notification(
            user,
            "streak_alert",
            "Streak on the line",
            "Complete a lesson tonight so your streak keeps climbing.",
            streak_alert_time if streak_alert_time > now else streak_alert_time + timedelta(days=1),
        )

    if user.boost_active and user.xp_boost_until:
        schedule_notification(
            user,
            "boost_active",
            "XP boost active",
            "You have an active XP boost. Use it before it expires.",
            boost_alert_time,
            {"expiresAt": user.xp_boost_until.isoformat()},
        )

    return (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.read_at.is_(None).desc(), Notification.scheduled_for.desc())
        .limit(8)
        .all()
    )
