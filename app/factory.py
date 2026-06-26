from __future__ import annotations

import os
from typing import Any

from flask import Flask

from app.extensions import db, login_manager, migrate
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
    from app.blueprints.cities import cities_bp
    from app.blueprints.main import main_bp
    from app.blueprints.settings import settings_bp
    from app.cli import register_cli
    from app.scheduler import init_scheduler

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(cities_bp)
    app.register_blueprint(settings_bp)
    init_admin(app)
    register_cli(app)

    if app.config["SCHEDULER_ENABLED"]:
        init_scheduler(app)

    return app
