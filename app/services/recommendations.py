from __future__ import annotations

from sqlalchemy import case, func

from app.extensions import db
from app.models.core import Lesson, QuestionAttempt, Recommendation, User, utcnow
from app.services.adaptive import lesson_completion_heatmap, recommendation_scores, weak_topics


def rebuild_recommendations(user: User) -> list[Recommendation]:
    Recommendation.query.filter_by(user_id=user.id).delete()
    scores = recommendation_scores(user)
    recommendations = []
    for lesson_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:5]:
        lesson = db.session.get(Lesson, lesson_id)
        if not lesson:
            continue
        reason = (
            f"Strengthen {lesson.topic.lower()} with spaced repetition"
            if score >= 1.5
            else f"Keep momentum in {lesson.topic.lower()}"
        )
        recommendation = Recommendation(user_id=user.id, lesson_id=lesson.id, reason=reason, score=score)
        db.session.add(recommendation)
        recommendations.append(recommendation)
    db.session.flush()
    return recommendations


def analytics_for_user(user: User) -> dict:
    attempts = (
        db.session.query(
            func.count(QuestionAttempt.id).label("total_attempts"),
            func.sum(case((QuestionAttempt.is_correct.is_(True), 1), else_=0)).label("correct_attempts"),
            func.avg(QuestionAttempt.response_time_ms).label("avg_response"),
        )
        .filter(QuestionAttempt.user_id == user.id)
        .one()
    )
    total_attempts = int(attempts.total_attempts or 0)
    correct_attempts = int(attempts.correct_attempts or 0)
    completion_count = sum(1 for entry in user.lesson_progress if entry.status == "completed")
    return {
        "totalAttempts": total_attempts,
        "accuracy": round((correct_attempts / total_attempts) * 100, 1) if total_attempts else 0,
        "avgResponseMs": round(float(attempts.avg_response or 0), 1),
        "completedLessons": completion_count,
        "weakTopics": weak_topics(user),
        "activity": lesson_completion_heatmap(user),
        "reviewQueue": sum(
            1
            for progress in user.lesson_progress
            if progress.next_review_at and progress.next_review_at <= utcnow()
        ),
    }
