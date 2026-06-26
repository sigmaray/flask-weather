from __future__ import annotations

from flask import Flask
from flask_admin import Admin

from app.admin_auth import SecureAdminIndexView
from app.admin_views import (
    AppSettingsAdmin,
    CityAdmin,
    ToolsAdmin,
    UserAdmin,
    WeatherRecordAdmin,
)
from app.extensions import db
from app.models import AppSettings, City, User, WeatherRecord


def init_admin(app: Flask) -> None:
    admin = Admin(
        app,
        name="Weather Admin",
        url="/admin",
        index_view=SecureAdminIndexView(),
    )
    admin.add_view(ToolsAdmin(name="Tools", endpoint="tools"))
    admin.add_view(UserAdmin(User, db.session, name="Users", endpoint="users"))
    admin.add_view(CityAdmin(City, db.session, name="Cities", endpoint="admin_cities"))
    admin.add_view(
        WeatherRecordAdmin(
            WeatherRecord,
            db.session,
            name="Weather",
            endpoint="weather_records",
        )
    )
    admin.add_view(
        AppSettingsAdmin(
            AppSettings,
            db.session,
            name="Settings",
            endpoint="app_settings",
        )
    )
