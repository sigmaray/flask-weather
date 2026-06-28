from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required, login_user, logout_user

from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
    if current_user.is_authenticated:
        return redirect(url_for("admin_cities.index_view"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
        else:
            login_user(user)
            next_page = request.args.get("next")
            from urllib.parse import urlparse
            if next_page and urlparse(next_page).netloc != "":
                next_page = None
            return redirect(next_page or url_for("admin_cities.index_view"))
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout() -> ResponseReturnValue:
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
