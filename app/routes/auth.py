from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models.core import Course, CourseEnrollment, Language, User

auth_bp = Blueprint("auth", __name__)


def auth_context() -> dict:
    return {
        "languages": Language.query.order_by(Language.name.asc()).all(),
        "courses": Course.query.order_by(Course.title.asc()).all(),
    }


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("auth.html", mode="login", **auth_context())
        login_user(user)
        return redirect(url_for("main.dashboard"))
    return render_template("auth.html", mode="login", **auth_context())


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        native_language_id = request.form.get("native_language_id", type=int)
        course_id = request.form.get("course_id", type=int)

        if not all([username, email, password, native_language_id, course_id]):
            flash("Complete every field to create an account.", "error")
            return render_template("auth.html", mode="signup", **auth_context())
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("That username or email is already in use.", "error")
            return render_template("auth.html", mode="signup", **auth_context())

        user = User(
            username=username,
            email=email,
            native_language_id=native_language_id,
            active_course_id=course_id,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        course = db.session.get(Course, course_id)
        first_unit = course.units[0] if course and course.units else None
        first_lesson = None
        if first_unit:
            first_lesson = next((lesson for lesson in first_unit.lessons if not lesson.is_placement), None)
        db.session.add(
            CourseEnrollment(
                user_id=user.id,
                course_id=course_id,
                current_unit_id=first_unit.id if first_unit else None,
                current_lesson_id=first_lesson.id if first_lesson else None,
            )
        )
        db.session.commit()
        login_user(user)
        return redirect(url_for("main.dashboard"))
    return render_template("auth.html", mode="signup", **auth_context())


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
