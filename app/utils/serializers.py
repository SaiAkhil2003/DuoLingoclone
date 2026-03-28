from __future__ import annotations

from datetime import datetime

from app.models.core import Lesson, Notification, Question, User
from app.services.translation_questions import build_question_payload


def serialize_question(question: Question) -> dict:
    payload = build_question_payload(question)
    return {
        "id": question.id,
        "prompt": payload["prompt"],
        "questionType": question.question_type,
        "choices": payload["choices"],
        "hint": payload["hint"],
        "explanation": payload["explanation"],
        "difficulty": question.difficulty,
        "topic": question.topic,
        "audioText": payload["audioText"],
        "speakingText": payload["speakingText"],
    }


def serialize_lesson_card(lesson: Lesson, progress_map: dict[int, object] | None = None) -> dict:
    progress = progress_map.get(lesson.id) if progress_map else None
    return {
        "id": lesson.id,
        "title": lesson.title,
        "description": lesson.description,
        "topic": lesson.topic,
        "difficulty": lesson.difficulty,
        "xpReward": lesson.xp_reward,
        "questionCount": len(lesson.questions),
        "status": getattr(progress, "status", "not_started"),
        "masteryLevel": round(getattr(progress, "mastery_level", 0.0), 2),
        "accuracy": round(getattr(progress, "accuracy", 0.0), 2),
        "nextReviewAt": (
            progress.next_review_at.isoformat() if getattr(progress, "next_review_at", None) else None
        ),
    }


def serialize_notification(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "type": notification.notification_type,
        "title": notification.title,
        "message": notification.message,
        "scheduledFor": notification.scheduled_for.isoformat(),
        "readAt": notification.read_at.isoformat() if notification.read_at else None,
        "payload": notification.payload or {},
    }


def serialize_user_summary(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "xp": user.xp,
        "level": user.level,
        "coins": user.coins,
        "dailyStreak": user.daily_streak,
        "longestStreak": user.longest_streak,
        "streakFreezes": user.streak_freezes,
        "boostActive": user.boost_active,
        "xpBoostMultiplier": user.effective_xp_multiplier,
        "avatarColor": user.avatar_color,
    }


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
