from __future__ import annotations

import os
from typing import Any

from flask import Flask, redirect, url_for
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from app.extensions import db, login_manager, migrate
from app.memory_log import log_app_error
from app.models import User


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-key"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "postgresql://weather:weather@localhost:5432/weather"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SCHEDULER_ENABLED=os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true",
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    from app.admin import init_admin
    from app.blueprints.auth import auth_bp
    from app.cli import register_cli
    from app.scheduler import init_scheduler
    from app.services.weather_codes import weather_code_label
    from app.vcr_setup import apply_vcr_if_e2e

    apply_vcr_if_e2e()

    app.jinja_env.filters["weather_code_label"] = weather_code_label

    app.register_blueprint(auth_bp)
    init_admin(app)
    register_cli(app)

    @app.route("/")
    def index() -> Any:
        if current_user.is_authenticated:
            return redirect(url_for("admin_cities.index_view"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(Exception)
    def log_unhandled_exception(exc: Exception) -> Any:
        if isinstance(exc, HTTPException):
            return exc
        log_app_error("unhandled", str(exc), exc)
        raise

    if app.config["SCHEDULER_ENABLED"]:
        init_scheduler(app)

    return app
