from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/lesson/<int:lesson_id>")
@login_required
def lesson(lesson_id: int):
    return render_template("lesson.html", lesson_id=lesson_id)


@main_bp.route("/social")
@login_required
def social():
    return render_template("social.html")
