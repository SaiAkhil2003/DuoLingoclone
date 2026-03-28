from __future__ import annotations

from datetime import date, datetime, timezone
from math import floor

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


LEAGUES = [
    "Bronze",
    "Silver",
    "Gold",
    "Sapphire",
    "Ruby",
    "Emerald",
    "Amethyst",
    "Pearl",
    "Obsidian",
    "Diamond",
]


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    native_language_id = db.Column(db.Integer, db.ForeignKey("languages.id"))
    active_course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    xp = db.Column(db.Integer, default=0, nullable=False)
    level = db.Column(db.Integer, default=1, nullable=False)
    coins = db.Column(db.Integer, default=50, nullable=False)
    daily_streak = db.Column(db.Integer, default=0, nullable=False)
    longest_streak = db.Column(db.Integer, default=0, nullable=False)
    streak_freezes = db.Column(db.Integer, default=2, nullable=False)
    last_active_date = db.Column(db.Date, nullable=True)
    xp_boost_multiplier = db.Column(db.Float, default=1.0, nullable=False)
    xp_boost_until = db.Column(db.DateTime(timezone=True), nullable=True)
    avatar_color = db.Column(db.String(20), default="#78c800", nullable=False)
    preferred_reminder_time = db.Column(db.String(5), default="19:00", nullable=False)

    enrollments = db.relationship("CourseEnrollment", back_populates="user", lazy=True)
    lesson_progress = db.relationship("LessonProgress", back_populates="user", lazy=True)
    question_attempts = db.relationship("QuestionAttempt", back_populates="user", lazy=True)
    achievements = db.relationship("UserAchievement", back_populates="user", lazy=True)
    notifications = db.relationship("Notification", back_populates="user", lazy=True)
    recommendations = db.relationship("Recommendation", back_populates="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def boost_active(self) -> bool:
        return bool(self.xp_boost_until and self.xp_boost_until > utcnow())

    @property
    def effective_xp_multiplier(self) -> float:
        return self.xp_boost_multiplier if self.boost_active else 1.0

    def recompute_level(self) -> None:
        self.level = max(1, floor(self.xp / 120) + 1)


class Language(TimestampMixin, db.Model):
    __tablename__ = "languages"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    translations = db.relationship("Translation", back_populates="language", lazy=True)


class TranslationGroup(TimestampMixin, db.Model):
    __tablename__ = "translation_groups"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    topic = db.Column(db.String(80), nullable=False)

    translations = db.relationship(
        "Translation",
        back_populates="translation_group",
        cascade="all, delete-orphan",
        lazy=True,
    )
    questions = db.relationship("Question", back_populates="translation_group", lazy=True)


class Translation(TimestampMixin, db.Model):
    __tablename__ = "translations"

    id = db.Column(db.Integer, primary_key=True)
    translation_group_id = db.Column(
        db.Integer, db.ForeignKey("translation_groups.id"), nullable=False
    )
    language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    alternate_texts = db.Column(db.JSON, nullable=True)
    example_sentence = db.Column(db.Text, nullable=True)

    translation_group = db.relationship("TranslationGroup", back_populates="translations")
    language = db.relationship("Language", back_populates="translations")

    __table_args__ = (
        db.UniqueConstraint(
            "translation_group_id",
            "language_id",
            name="uq_translation_group_language",
        ),
    )


class Course(TimestampMixin, db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    source_language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    target_language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False)
    cefr_level = db.Column(db.String(10), default="A1", nullable=False)
    accent_color = db.Column(db.String(20), default="#58cc02", nullable=False)

    source_language = db.relationship("Language", foreign_keys=[source_language_id])
    target_language = db.relationship("Language", foreign_keys=[target_language_id])
    units = db.relationship("Unit", back_populates="course", order_by="Unit.position", lazy=True)
    enrollments = db.relationship("CourseEnrollment", back_populates="course", lazy=True)


class Unit(TimestampMixin, db.Model):
    __tablename__ = "units"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False)

    course = db.relationship("Course", back_populates="units")
    lessons = db.relationship("Lesson", back_populates="unit", order_by="Lesson.position", lazy=True)


class Lesson(TimestampMixin, db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.Integer, default=1, nullable=False)
    xp_reward = db.Column(db.Integer, default=40, nullable=False)
    is_placement = db.Column(db.Boolean, default=False, nullable=False)

    unit = db.relationship("Unit", back_populates="lessons")
    questions = db.relationship("Question", back_populates="lesson", lazy=True)
    progress_entries = db.relationship("LessonProgress", back_populates="lesson", lazy=True)


class Question(TimestampMixin, db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    translation_group_id = db.Column(
        db.Integer, db.ForeignKey("translation_groups.id"), nullable=True
    )
    prompt = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(40), nullable=False)
    choices = db.Column(db.JSON, nullable=True)
    correct_answer = db.Column(db.String(255), nullable=False)
    acceptable_answers = db.Column(db.JSON, nullable=True)
    hint = db.Column(db.String(255), nullable=True)
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.Integer, default=1, nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    audio_text = db.Column(db.Text, nullable=True)
    speaking_text = db.Column(db.Text, nullable=True)

    lesson = db.relationship("Lesson", back_populates="questions")
    translation_group = db.relationship("TranslationGroup", back_populates="questions")


class CourseEnrollment(TimestampMixin, db.Model):
    __tablename__ = "course_enrollments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    current_unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=True)
    current_lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=True)
    proficiency_score = db.Column(db.Float, default=0.0, nullable=False)
    placement_level = db.Column(db.Integer, default=1, nullable=False)

    user = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")
    current_unit = db.relationship("Unit", foreign_keys=[current_unit_id])
    current_lesson = db.relationship("Lesson", foreign_keys=[current_lesson_id])

    __table_args__ = (
        db.UniqueConstraint("user_id", "course_id", name="uq_user_course"),
    )


class LessonProgress(TimestampMixin, db.Model):
    __tablename__ = "lesson_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    status = db.Column(db.String(20), default="not_started", nullable=False)
    attempts_count = db.Column(db.Integer, default=0, nullable=False)
    accuracy = db.Column(db.Float, default=0.0, nullable=False)
    best_score = db.Column(db.Float, default=0.0, nullable=False)
    last_score = db.Column(db.Float, default=0.0, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    mastery_level = db.Column(db.Float, default=0.0, nullable=False)
    next_review_at = db.Column(db.DateTime(timezone=True), nullable=True)
    easiness_factor = db.Column(db.Float, default=2.5, nullable=False)
    review_interval_days = db.Column(db.Integer, default=1, nullable=False)

    user = db.relationship("User", back_populates="lesson_progress")
    lesson = db.relationship("Lesson", back_populates="progress_entries")

    __table_args__ = (
        db.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),
    )


class QuestionAttempt(TimestampMixin, db.Model):
    __tablename__ = "question_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False)
    response_time_ms = db.Column(db.Integer, nullable=True)
    difficulty_snapshot = db.Column(db.Integer, nullable=False)
    xp_awarded = db.Column(db.Integer, default=0, nullable=False)
    answered_on = db.Column(db.Date, default=date.today, nullable=False)

    user = db.relationship("User", back_populates="question_attempts")
    question = db.relationship("Question")
    lesson = db.relationship("Lesson")


class Achievement(TimestampMixin, db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(40), default="star", nullable=False)
    criteria_type = db.Column(db.String(40), nullable=False)
    criteria_value = db.Column(db.Integer, nullable=False)
    xp_reward = db.Column(db.Integer, default=0, nullable=False)
    coins_reward = db.Column(db.Integer, default=0, nullable=False)


class UserAchievement(TimestampMixin, db.Model):
    __tablename__ = "user_achievements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievements.id"), nullable=False)
    earned_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="achievements")
    achievement = db.relationship("Achievement")

    __table_args__ = (
        db.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )


class Friendship(TimestampMixin, db.Model):
    __tablename__ = "friendships"

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    addressee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    requester = db.relationship("User", foreign_keys=[requester_id])
    addressee = db.relationship("User", foreign_keys=[addressee_id])

    __table_args__ = (
        db.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
    )


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notification_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    scheduled_for = db.Column(db.DateTime(timezone=True), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    payload = db.Column(db.JSON, nullable=True)

    user = db.relationship("User", back_populates="notifications")


class Recommendation(TimestampMixin, db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Float, nullable=False)

    user = db.relationship("User", back_populates="recommendations")
    lesson = db.relationship("Lesson")


class LeaderboardEntry(TimestampMixin, db.Model):
    __tablename__ = "leaderboard_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    week_start = db.Column(db.Date, nullable=False, index=True)
    xp_earned = db.Column(db.Integer, default=0, nullable=False)
    rank = db.Column(db.Integer, default=0, nullable=False)
    league_name = db.Column(db.String(40), default="Bronze", nullable=False)

    user = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("user_id", "week_start", name="uq_user_week_leaderboard"),
    )


class UserLeagueHistory(TimestampMixin, db.Model):
    __tablename__ = "user_league_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    league_name = db.Column(db.String(40), nullable=False)
    finish_rank = db.Column(db.Integer, nullable=False)
    xp_earned = db.Column(db.Integer, default=0, nullable=False)

    user = db.relationship("User")


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))
