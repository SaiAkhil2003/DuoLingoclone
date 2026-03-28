from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'duolingo_clone.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMINDER_HOUR = int(os.environ.get("REMINDER_HOUR", "19"))
    STREAK_GRACE_HOURS = int(os.environ.get("STREAK_GRACE_HOURS", "24"))
    XP_PER_CORRECT = int(os.environ.get("XP_PER_CORRECT", "12"))
    COINS_PER_LESSON = int(os.environ.get("COINS_PER_LESSON", "5"))
