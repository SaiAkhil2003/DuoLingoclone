from __future__ import annotations

from sqlalchemy import and_, or_

from app.extensions import db
from app.models.core import Friendship, LeaderboardEntry, User
from app.services.gamification import start_of_week


def send_friend_request(sender: User, username: str) -> tuple[bool, str]:
    target = User.query.filter_by(username=username).first()
    if not target:
        return False, "User not found."
    if target.id == sender.id:
        return False, "You cannot add yourself."
    existing = Friendship.query.filter(
        or_(
            and_(Friendship.requester_id == sender.id, Friendship.addressee_id == target.id),
            and_(Friendship.requester_id == target.id, Friendship.addressee_id == sender.id),
        )
    ).first()
    if existing:
        return False, "Friend request already exists."
    db.session.add(Friendship(requester_id=sender.id, addressee_id=target.id))
    db.session.flush()
    return True, f"Friend request sent to {target.username}."


def respond_to_friend_request(user: User, friendship_id: int, accept: bool) -> tuple[bool, str]:
    relation = db.session.get(Friendship, friendship_id)
    if not relation or relation.addressee_id != user.id or relation.status != "pending":
        return False, "Friend request not available."
    if accept:
        relation.status = "accepted"
        from app.models.core import utcnow

        relation.accepted_at = utcnow()
        return True, "Friend request accepted."
    db.session.delete(relation)
    return True, "Friend request declined."


def social_snapshot(user: User) -> dict:
    accepted = Friendship.query.filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
    ).all()
    pending = Friendship.query.filter_by(addressee_id=user.id, status="pending").all()
    friend_ids = [
        relation.addressee_id if relation.requester_id == user.id else relation.requester_id
        for relation in accepted
    ]
    friends = User.query.filter(User.id.in_(friend_ids)).order_by(User.xp.desc()).all() if friend_ids else []

    week_start = start_of_week()
    leaderboard_map = {
        entry.user_id: entry
        for entry in LeaderboardEntry.query.filter(LeaderboardEntry.week_start == week_start).all()
    }
    return {
        "friends": [
            {
                "id": friend.id,
                "username": friend.username,
                "xp": friend.xp,
                "level": friend.level,
                "dailyStreak": friend.daily_streak,
                "league": leaderboard_map.get(friend.id).league_name if leaderboard_map.get(friend.id) else "Bronze",
            }
            for friend in friends
        ],
        "pending": [
            {
                "id": request.id,
                "username": request.requester.username,
                "createdAt": request.created_at.isoformat(),
            }
            for request in pending
        ],
    }
