from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlalchemy import case, func

from app.extensions import db
from app.models.core import CourseEnrollment, Lesson, LessonProgress, Question, QuestionAttempt, User, utcnow
from app.services.translation_questions import accepted_answers_for_question


def normalize_answer(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def answer_is_correct(question: Question, submitted_answer: str | None) -> bool:
    normalized = normalize_answer(submitted_answer)
    valid_answers = set()
    if not question.translation_group_id:
        valid_answers.add(normalize_answer(question.correct_answer))
    for answer in accepted_answers_for_question(question):
        valid_answers.add(normalize_answer(answer))
    return normalized in valid_answers


def get_or_create_progress(user: User, lesson: Lesson) -> LessonProgress:
    progress = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson.id).first()
    if not progress:
        progress = LessonProgress(user_id=user.id, lesson_id=lesson.id)
        db.session.add(progress)
        db.session.flush()
    return progress


def get_lesson_questions_for_user(user: User, lesson: Lesson) -> list[Question]:
    attempts = (
        db.session.query(
            QuestionAttempt.question_id,
            func.avg(case((QuestionAttempt.is_correct.is_(True), 1), else_=0)).label("accuracy"),
            func.count(QuestionAttempt.id).label("attempt_count"),
        )
        .filter(
            QuestionAttempt.user_id == user.id,
            QuestionAttempt.lesson_id == lesson.id,
        )
        .group_by(QuestionAttempt.question_id)
        .all()
    )
    stats = {row.question_id: {"accuracy": row.accuracy or 0, "attempts": row.attempt_count} for row in attempts}

    def sort_key(question: Question) -> tuple[float, int]:
        stat = stats.get(question.id, {"accuracy": 0.0, "attempts": 0})
        need_score = (1 - stat["accuracy"]) + (0.5 if stat["attempts"] == 0 else 0)
        return (-need_score, question.difficulty)

    return sorted(lesson.questions, key=sort_key)


def update_spaced_repetition(progress: LessonProgress, score_ratio: float) -> None:
    quality = max(0, min(5, round(score_ratio * 5)))
    progress.easiness_factor = max(
        1.3,
        progress.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    if quality < 3:
        progress.review_interval_days = 1
    elif progress.review_interval_days <= 1:
        progress.review_interval_days = 2
    else:
        progress.review_interval_days = int(progress.review_interval_days * progress.easiness_factor)
    progress.next_review_at = utcnow() + timedelta(days=progress.review_interval_days)
    progress.mastery_level = min(
        1.0,
        (progress.mastery_level * 0.4)
        + (score_ratio * 0.4)
        + min(progress.review_interval_days / 30, 1.0) * 0.2,
    )


def select_next_lesson(user: User, enrollment: CourseEnrollment) -> Lesson | None:
    course = enrollment.course
    progress_map = {entry.lesson_id: entry for entry in user.lesson_progress}

    review_candidates = []
    new_candidates = []
    for unit in course.units:
        for lesson in unit.lessons:
            if lesson.is_placement:
                continue
            progress = progress_map.get(lesson.id)
            if progress and progress.next_review_at and progress.next_review_at <= utcnow():
                review_candidates.append((progress.mastery_level, lesson))
            elif not progress or progress.status != "completed":
                new_candidates.append((lesson.difficulty, unit.position, lesson.position, lesson))

    if review_candidates:
        review_candidates.sort(key=lambda item: item[0])
        return review_candidates[0][1]
    if new_candidates:
        new_candidates.sort(key=lambda item: item[:3])
        return new_candidates[0][3]
    all_lessons = [lesson for unit in course.units for lesson in unit.lessons if not lesson.is_placement]
    return all_lessons[0] if all_lessons else None


def update_enrollment_position(user: User, lesson: Lesson) -> None:
    enrollment = CourseEnrollment.query.filter_by(user_id=user.id, course_id=lesson.unit.course.id).first()
    if not enrollment:
        return
    enrollment.current_unit_id = lesson.unit.id
    enrollment.current_lesson_id = lesson.id
    user.active_course_id = lesson.unit.course.id


def topic_accuracy_by_user(user: User) -> dict[str, float]:
    rows = (
        db.session.query(
            Question.topic,
            func.avg(case((QuestionAttempt.is_correct.is_(True), 1), else_=0)).label("accuracy"),
        )
        .join(Question, Question.id == QuestionAttempt.question_id)
        .filter(QuestionAttempt.user_id == user.id)
        .group_by(Question.topic)
        .all()
    )
    return {row.topic: round((row.accuracy or 0) * 100, 1) for row in rows}


def lesson_completion_heatmap(user: User) -> list[dict]:
    rows = (
        db.session.query(
            QuestionAttempt.answered_on,
            func.sum(case((QuestionAttempt.is_correct.is_(True), 1), else_=0)).label("correct_count"),
            func.count(QuestionAttempt.id).label("total_count"),
        )
        .filter(QuestionAttempt.user_id == user.id)
        .group_by(QuestionAttempt.answered_on)
        .order_by(QuestionAttempt.answered_on.desc())
        .limit(14)
        .all()
    )
    return [
        {
            "date": row.answered_on.isoformat(),
            "correct": int(row.correct_count or 0),
            "total": row.total_count,
        }
        for row in reversed(rows)
    ]


def weak_topics(user: User) -> list[dict]:
    accuracies = topic_accuracy_by_user(user)
    ranked = sorted(accuracies.items(), key=lambda item: item[1])
    return [{"topic": topic, "accuracy": accuracy} for topic, accuracy in ranked[:4]]


def recommendation_scores(user: User) -> dict[int, float]:
    scores = defaultdict(float)
    weak_topic_map = {item["topic"]: item["accuracy"] for item in weak_topics(user)}
    for progress in user.lesson_progress:
        if progress.next_review_at and progress.mastery_level < 0.75:
            scores[progress.lesson_id] += 2.0 - progress.mastery_level
        scores[progress.lesson_id] += max(0, 1.0 - progress.accuracy)
    for lesson in Lesson.query.all():
        if lesson.topic in weak_topic_map:
            scores[lesson.id] += (100 - weak_topic_map[lesson.topic]) / 100
    if not scores:
        for enrollment in user.enrollments:
            if enrollment.current_lesson_id:
                scores[enrollment.current_lesson_id] = 1.0
            elif enrollment.course.units:
                first_unit = enrollment.course.units[0]
                first_lesson = next((lesson for lesson in first_unit.lessons if not lesson.is_placement), None)
                if first_lesson:
                    scores[first_lesson.id] = 1.0
    return scores
