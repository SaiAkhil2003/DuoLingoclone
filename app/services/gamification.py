from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, or_

from app.extensions import db
from app.models.core import (
    Achievement,
    LeaderboardEntry,
    Lesson,
    QuestionAttempt,
    User,
    UserAchievement,
    UserLeagueHistory,
    utcnow,
)


def start_of_week(target: date | None = None) -> date:
    target = target or date.today()
    return target - timedelta(days=target.weekday())


def update_streak(user: User) -> None:
    today = date.today()
    if user.last_active_date == today:
        return
    if user.last_active_date == today - timedelta(days=1):
        user.daily_streak += 1
    elif user.last_active_date and user.last_active_date < today - timedelta(days=1):
        missed_days = (today - user.last_active_date).days - 1
        if missed_days == 1 and user.streak_freezes > 0:
            user.streak_freezes -= 1
            user.daily_streak += 1
        else:
            user.daily_streak = 1
    else:
        user.daily_streak = 1
    user.longest_streak = max(user.longest_streak, user.daily_streak)
    user.last_active_date = today


def apply_xp_and_coins(user: User, lesson: Lesson, correct_count: int, total_count: int) -> tuple[int, int]:
    base_xp = int((lesson.xp_reward / max(total_count, 1)) * correct_count)
    xp = round(base_xp * user.effective_xp_multiplier)
    coins = 5 + (2 if correct_count == total_count else 0)
    user.xp += xp
    user.coins += coins
    user.recompute_level()
    update_streak(user)
    return xp, coins


def maybe_activate_boost(user: User) -> bool:
    if user.coins >= 120 and not user.boost_active and user.daily_streak >= 3:
        user.coins -= 120
        user.xp_boost_multiplier = 1.5
        user.xp_boost_until = utcnow() + timedelta(hours=12)
        return True
    return False


def evaluate_achievements(user: User) -> list[dict]:
    earned = []
    existing_ids = {entry.achievement_id for entry in user.achievements}
    lessons_completed = sum(1 for entry in user.lesson_progress if entry.status == "completed")
    perfect_lessons = sum(1 for entry in user.lesson_progress if entry.best_score == 1.0)
    friend_count = len({*get_friend_ids(user.id)})
    criteria_state = {
        "xp": user.xp,
        "streak": user.daily_streak,
        "lessons": lessons_completed,
        "perfect_lessons": perfect_lessons,
        "friends": friend_count,
        "coins": user.coins,
    }

    for achievement in Achievement.query.order_by(Achievement.id).all():
        if achievement.id in existing_ids:
            continue
        if criteria_state.get(achievement.criteria_type, 0) >= achievement.criteria_value:
            user_achievement = UserAchievement(user_id=user.id, achievement_id=achievement.id)
            db.session.add(user_achievement)
            user.xp += achievement.xp_reward
            user.coins += achievement.coins_reward
            user.recompute_level()
            earned.append(
                {
                    "name": achievement.name,
                    "description": achievement.description,
                    "xpReward": achievement.xp_reward,
                    "coinsReward": achievement.coins_reward,
                    "icon": achievement.icon,
                }
            )
    return earned


def get_friend_ids(user_id: int) -> set[int]:
    from app.models.core import Friendship

    accepted = Friendship.query.filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
    ).all()
    friend_ids = set()
    for relation in accepted:
        friend_ids.add(relation.addressee_id if relation.requester_id == user_id else relation.requester_id)
    return friend_ids


def refresh_weekly_leaderboard() -> list[LeaderboardEntry]:
    week_start = start_of_week()
    users = User.query.order_by(User.xp.desc()).all()
    totals = {
        row.user_id: row.xp_earned
        for row in db.session.query(
            QuestionAttempt.user_id,
            func.sum(QuestionAttempt.xp_awarded).label("xp_earned"),
        )
        .filter(QuestionAttempt.answered_on >= week_start)
        .group_by(QuestionAttempt.user_id)
        .all()
    }
    participant_count = max(len(users), 1)
    entries = []
    for rank, user in enumerate(sorted(users, key=lambda item: totals.get(item.id, 0), reverse=True), start=1):
        percentile = (rank - 1) / participant_count
        league_index = min(int(percentile * 10), 9)
        league_name = [
            "Diamond",
            "Obsidian",
            "Pearl",
            "Amethyst",
            "Emerald",
            "Ruby",
            "Sapphire",
            "Gold",
            "Silver",
            "Bronze",
        ][league_index]
        entry = LeaderboardEntry.query.filter_by(user_id=user.id, week_start=week_start).first()
        if not entry:
            entry = LeaderboardEntry(user_id=user.id, week_start=week_start)
            db.session.add(entry)
        entry.xp_earned = int(totals.get(user.id, 0))
        entry.rank = rank
        entry.league_name = league_name
        entries.append(entry)
    db.session.flush()
    return entries


def snapshot_previous_week() -> None:
    week_start = start_of_week()
    prior_week_start = week_start - timedelta(days=7)
    entries = LeaderboardEntry.query.filter_by(week_start=prior_week_start).all()
    for entry in entries:
        exists = UserLeagueHistory.query.filter_by(user_id=entry.user_id, week_start=prior_week_start).first()
        if exists:
            continue
        db.session.add(
            UserLeagueHistory(
                user_id=entry.user_id,
                week_start=prior_week_start,
                week_end=prior_week_start + timedelta(days=6),
                league_name=entry.league_name,
                finish_rank=entry.rank,
                xp_earned=entry.xp_earned,
            )
        )


def league_summary_for_user(user: User) -> dict:
    week_start = start_of_week()
    entry = LeaderboardEntry.query.filter_by(user_id=user.id, week_start=week_start).first()
    history = (
        UserLeagueHistory.query.filter_by(user_id=user.id)
        .order_by(UserLeagueHistory.week_start.desc())
        .limit(3)
        .all()
    )
    return {
        "currentLeague": entry.league_name if entry else "Bronze",
        "currentRank": entry.rank if entry else None,
        "weeklyXp": entry.xp_earned if entry else 0,
        "history": [
            {
                "weekStart": item.week_start.isoformat(),
                "leagueName": item.league_name,
                "rank": item.finish_rank,
                "xp": item.xp_earned,
            }
            for item in history
        ],
    }
