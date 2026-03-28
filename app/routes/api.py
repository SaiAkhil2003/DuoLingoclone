from __future__ import annotations

from statistics import mean

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models.core import (
    Course,
    CourseEnrollment,
    LeaderboardEntry,
    Lesson,
    Notification,
    Question,
    QuestionAttempt,
    User,
)
from app.services.adaptive import (
    answer_is_correct,
    get_lesson_questions_for_user,
    get_or_create_progress,
    select_next_lesson,
    update_enrollment_position,
    update_spaced_repetition,
)
from app.services.gamification import (
    apply_xp_and_coins,
    evaluate_achievements,
    league_summary_for_user,
    maybe_activate_boost,
    refresh_weekly_leaderboard,
    snapshot_previous_week,
    start_of_week,
)
from app.services.notifications import refresh_notifications
from app.services.recommendations import analytics_for_user, rebuild_recommendations
from app.services.social import respond_to_friend_request, send_friend_request, social_snapshot
from app.services.translation_questions import accepted_answers_for_question, explanation_for_question
from app.utils.serializers import (
    serialize_lesson_card,
    serialize_notification,
    serialize_question,
    serialize_user_summary,
)

api_bp = Blueprint("api", __name__)


def course_payload_for_user(user: User) -> list[dict]:
    progress_map = {entry.lesson_id: entry for entry in user.lesson_progress}
    enrollments = {entry.course_id: entry for entry in user.enrollments}
    payload = []
    for course in Course.query.order_by(Course.title.asc()).all():
        enrollment = enrollments.get(course.id)
        payload.append(
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "accentColor": course.accent_color,
                "sourceLanguage": course.source_language.name,
                "sourceLanguageCode": course.source_language.code,
                "targetLanguage": course.target_language.name,
                "targetLanguageCode": course.target_language.code,
                "translationDirection": (
                    f"Translate from {course.source_language.name} to {course.target_language.name}"
                ),
                "cefrLevel": course.cefr_level,
                "enrolled": bool(enrollment),
                "proficiencyScore": round(enrollment.proficiency_score, 2) if enrollment else 0,
                "units": [
                    {
                        "id": unit.id,
                        "title": unit.title,
                        "description": unit.description,
                        "position": unit.position,
                        "lessons": [serialize_lesson_card(lesson, progress_map) for lesson in unit.lessons],
                    }
                    for unit in course.units
                ],
            }
        )
    return payload


def global_leaderboard_payload() -> dict:
    weekly_entries = refresh_weekly_leaderboard()
    week_start = start_of_week()
    global_users = User.query.order_by(User.xp.desc()).limit(10).all()
    weekly = (
        LeaderboardEntry.query.filter_by(week_start=week_start)
        .order_by(LeaderboardEntry.rank.asc())
        .limit(10)
        .all()
    )
    return {
        "global": [
            {
                "rank": index,
                "username": user.username,
                "xp": user.xp,
                "level": user.level,
            }
            for index, user in enumerate(global_users, start=1)
        ],
        "weekly": [
            {
                "rank": entry.rank,
                "username": entry.user.username,
                "xp": entry.xp_earned,
                "league": entry.league_name,
            }
            for entry in weekly
        ],
        "participantCount": len(weekly_entries),
    }


def earned_achievements_payload(user: User) -> list[dict]:
    return [
        {
            "id": entry.id,
            "name": entry.achievement.name,
            "description": entry.achievement.description,
            "icon": entry.achievement.icon,
            "earnedAt": entry.earned_at.isoformat(),
        }
        for entry in sorted(user.achievements, key=lambda item: item.earned_at, reverse=True)
    ]


@api_bp.get("/dashboard")
@login_required
def dashboard_data():
    snapshot_previous_week()
    refresh_weekly_leaderboard()
    rebuild_recommendations(current_user)
    notifications = refresh_notifications(current_user)
    db.session.commit()

    active_enrollment = next(
        (entry for entry in current_user.enrollments if entry.course_id == current_user.active_course_id),
        current_user.enrollments[0] if current_user.enrollments else None,
    )
    next_lesson = select_next_lesson(current_user, active_enrollment) if active_enrollment else None

    return jsonify(
        {
            "user": serialize_user_summary(current_user),
            "courses": course_payload_for_user(current_user),
            "analytics": analytics_for_user(current_user),
            "recommendations": [
                {
                    "lessonId": recommendation.lesson.id,
                    "lessonTitle": recommendation.lesson.title,
                    "courseTitle": recommendation.lesson.unit.course.title,
                    "reason": recommendation.reason,
                    "score": round(recommendation.score, 2),
                }
                for recommendation in current_user.recommendations
            ],
            "leaderboards": global_leaderboard_payload(),
            "league": league_summary_for_user(current_user),
            "social": social_snapshot(current_user),
            "notifications": [serialize_notification(item) for item in notifications],
            "achievements": earned_achievements_payload(current_user),
            "nextLesson": next_lesson.id if next_lesson else None,
        }
    )


@api_bp.get("/lessons/<int:lesson_id>")
@login_required
def lesson_details(lesson_id: int):
    lesson = Lesson.query.get_or_404(lesson_id)
    questions = get_lesson_questions_for_user(current_user, lesson)
    return jsonify(
        {
            "lesson": {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "topic": lesson.topic,
                "difficulty": lesson.difficulty,
                "xpReward": lesson.xp_reward,
                "courseId": lesson.unit.course.id,
                "courseTitle": lesson.unit.course.title,
                "unitTitle": lesson.unit.title,
                "sourceLanguage": lesson.unit.course.source_language.name,
                "sourceLanguageCode": lesson.unit.course.source_language.code,
                "targetLanguage": lesson.unit.course.target_language.name,
                "targetLanguageCode": lesson.unit.course.target_language.code,
                "translationDirection": (
                    f"Translate from {lesson.unit.course.source_language.name} "
                    f"to {lesson.unit.course.target_language.name}"
                ),
                "isPlacement": lesson.is_placement,
            },
            "questions": [serialize_question(question) for question in questions],
        }
    )


@api_bp.post("/questions/<int:question_id>/check")
@login_required
def check_question(question_id: int):
    question = db.session.get(Question, question_id)
    if not question:
        return jsonify({"error": "Question not found."}), 404
    payload = request.get_json(force=True)
    answer = payload.get("answer", "")
    is_correct = answer_is_correct(question, answer)
    return jsonify(
        {
            "correct": is_correct,
            "acceptedAnswers": accepted_answers_for_question(question),
            "explanation": explanation_for_question(question),
        }
    )


@api_bp.post("/lessons/<int:lesson_id>/submit")
@login_required
def submit_lesson(lesson_id: int):
    lesson = Lesson.query.get_or_404(lesson_id)
    payload = request.get_json(force=True)
    submitted_answers = payload.get("answers", [])
    question_lookup = {question.id: question for question in lesson.questions}
    results = []
    correct_count = 0

    for item in submitted_answers:
        question = question_lookup.get(item.get("questionId"))
        if not question:
            continue
        answer = item.get("answer", "")
        is_correct = answer_is_correct(question, answer)
        correct_count += int(is_correct)
        attempt_xp = round((lesson.xp_reward / max(len(lesson.questions), 1)) * int(is_correct) * current_user.effective_xp_multiplier)
        db.session.add(
            QuestionAttempt(
                user_id=current_user.id,
                lesson_id=lesson.id,
                question_id=question.id,
                user_answer=answer,
                is_correct=is_correct,
                response_time_ms=item.get("responseTimeMs"),
                difficulty_snapshot=question.difficulty,
                xp_awarded=attempt_xp,
            )
        )
        results.append(
            {
                "questionId": question.id,
                "correct": is_correct,
                "acceptedAnswers": accepted_answers_for_question(question),
                "explanation": explanation_for_question(question),
            }
        )

    total_count = max(len(lesson.questions), 1)
    score_ratio = correct_count / total_count
    progress = get_or_create_progress(current_user, lesson)
    progress.attempts_count += 1
    progress.last_score = score_ratio
    progress.best_score = max(progress.best_score, score_ratio)
    progress.accuracy = (
        ((progress.accuracy * (progress.attempts_count - 1)) + score_ratio) / progress.attempts_count
    )
    progress.status = "completed" if score_ratio >= 0.6 else "in_progress"
    if score_ratio >= 0.6:
        from app.models.core import utcnow

        progress.completed_at = utcnow()
    update_spaced_repetition(progress, score_ratio)

    xp_earned, coins_earned = apply_xp_and_coins(current_user, lesson, correct_count, total_count)
    achievements = evaluate_achievements(current_user)
    boost_triggered = maybe_activate_boost(current_user)
    update_enrollment_position(current_user, lesson)

    db.session.commit()
    refresh_weekly_leaderboard()
    db.session.commit()

    return jsonify(
        {
            "score": round(score_ratio, 2),
            "correctCount": correct_count,
            "totalCount": total_count,
            "xpEarned": xp_earned,
            "coinsEarned": coins_earned,
            "boostTriggered": boost_triggered,
            "results": results,
            "achievements": achievements,
        }
    )


@api_bp.post("/courses/<int:course_id>/enroll")
@login_required
def enroll_course(course_id: int):
    course = Course.query.get_or_404(course_id)
    enrollment = CourseEnrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        first_unit = course.units[0] if course.units else None
        first_lesson = next((lesson for lesson in first_unit.lessons if not lesson.is_placement), None) if first_unit else None
        enrollment = CourseEnrollment(
            user_id=current_user.id,
            course_id=course_id,
            current_unit_id=first_unit.id if first_unit else None,
            current_lesson_id=first_lesson.id if first_lesson else None,
        )
        db.session.add(enrollment)
    current_user.active_course_id = course_id
    db.session.commit()
    return jsonify({"message": f"{course.title} is now active."})


@api_bp.get("/courses/<int:course_id>/placement-test")
@login_required
def placement_test(course_id: int):
    course = Course.query.get_or_404(course_id)
    placement_lesson = next(
        (lesson for unit in course.units for lesson in unit.lessons if lesson.is_placement),
        None,
    )
    if not placement_lesson:
        return jsonify({"error": "Placement test unavailable."}), 404
    questions = get_lesson_questions_for_user(current_user, placement_lesson)
    return jsonify(
        {
            "lesson": {"id": placement_lesson.id, "title": placement_lesson.title, "courseId": course.id},
            "questions": [serialize_question(question) for question in questions],
        }
    )


@api_bp.post("/courses/<int:course_id>/placement-test")
@login_required
def submit_placement_test(course_id: int):
    course = Course.query.get_or_404(course_id)
    placement_lesson = next(
        (lesson for unit in course.units for lesson in unit.lessons if lesson.is_placement),
        None,
    )
    if not placement_lesson:
        return jsonify({"error": "Placement test unavailable."}), 404
    payload = request.get_json(force=True)
    answers = payload.get("answers", [])
    correct_ratios = []
    for item in answers:
        question = db.session.get(Question, item.get("questionId"))
        if question:
            correct_ratios.append(1 if answer_is_correct(question, item.get("answer")) else 0)
    proficiency = mean(correct_ratios) if correct_ratios else 0
    enrollment = CourseEnrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        enrollment = CourseEnrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(enrollment)
    lessons = [lesson for unit in course.units for lesson in unit.lessons if not lesson.is_placement]
    index = min(len(lessons) - 1, int(proficiency * len(lessons))) if lessons else 0
    target_lesson = lessons[index] if lessons else None
    enrollment.proficiency_score = proficiency
    enrollment.placement_level = max(1, index + 1)
    enrollment.current_unit_id = target_lesson.unit.id if target_lesson else None
    enrollment.current_lesson_id = target_lesson.id if target_lesson else None
    current_user.active_course_id = course_id
    db.session.commit()
    return jsonify(
        {
            "proficiencyScore": round(proficiency, 2),
            "recommendedLessonId": target_lesson.id if target_lesson else None,
            "recommendedLessonTitle": target_lesson.title if target_lesson else None,
        }
    )


@api_bp.post("/friends/request")
@login_required
def friend_request():
    payload = request.get_json(force=True)
    ok, message = send_friend_request(current_user, payload.get("username", "").strip())
    db.session.commit()
    return jsonify({"message": message}), (200 if ok else 400)


@api_bp.post("/friends/respond")
@login_required
def friend_respond():
    payload = request.get_json(force=True)
    ok, message = respond_to_friend_request(current_user, payload.get("friendshipId"), bool(payload.get("accept")))
    achievements = []
    if ok and payload.get("accept"):
        achievements = evaluate_achievements(current_user)
    db.session.commit()
    return jsonify({"message": message, "achievements": achievements}), (200 if ok else 400)


@api_bp.get("/social")
@login_required
def social_data():
    refresh_weekly_leaderboard()
    db.session.commit()
    return jsonify(social_snapshot(current_user))


@api_bp.get("/leaderboards")
@login_required
def leaderboards():
    refresh_weekly_leaderboard()
    db.session.commit()
    return jsonify(global_leaderboard_payload())


@api_bp.post("/notifications/<int:notification_id>/read")
@login_required
def mark_notification(notification_id: int):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({"error": "Not found."}), 404
    from app.models.core import utcnow

    notification.read_at = utcnow()
    db.session.commit()
    return jsonify({"message": "Notification marked as read."})
