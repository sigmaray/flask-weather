from __future__ import annotations

from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from werkzeug.wrappers.response import Response

from app.extensions import db
from app.models import AppSettings, City, User, WeatherRecord


class SecureModelView(ModelView):  # type: ignore[misc]
    def is_accessible(self) -> bool:
        return bool(current_user.is_authenticated)

    def inaccessible_callback(self, name: str, **kwargs: object) -> Response:
        from flask import redirect, url_for

        return redirect(url_for("auth.login", next=kwargs.get("url")))


def init_admin(app: Flask) -> None:
    admin = Admin(app, name="Weather Admin")
    admin.add_view(SecureModelView(User, db.session, category="Admin"))
    admin.add_view(SecureModelView(City, db.session, category="Data"))
    admin.add_view(SecureModelView(WeatherRecord, db.session, category="Data"))
    admin.add_view(SecureModelView(AppSettings, db.session, category="Config"))
