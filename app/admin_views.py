from __future__ import annotations

import json
from typing import Any

from flask import flash, redirect, request, url_for
from flask_admin import expose
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_login import current_user
from werkzeug.wrappers.response import Response
from wtforms import PasswordField, validators

from app.admin_auth import SecureBaseView, SecureModelView
from app.extensions import db
from app.models import AppSettings, City


def _city_weather_context(city: City) -> dict[str, Any]:
    records = list(city.weather_records)[:100]
    chronological = list(reversed(records))
    chart_data = {
        "labels": [r.recorded_at.strftime("%Y-%m-%d %H:%M") for r in chronological],
        "temperatures": [r.temperature_c for r in chronological],
        "humidity": [r.humidity_percent for r in chronological],
        "wind": [r.wind_speed_ms for r in chronological],
    }
    return {
        "city": city,
        "records": records,
        "chart_data_json": json.dumps(chart_data),
        "default_interval": AppSettings.get_singleton().default_check_interval_minutes,
    }


class UserAdmin(SecureModelView):
    column_list = ["id", "username", "created_at"]
    column_searchable_list = ["username"]
    column_sortable_list = ["id", "username", "created_at"]
    column_default_sort = ("id", False)
    column_exclude_list = ["password_hash"]
    form_excluded_columns = ["password_hash"]

    column_labels = {
        "id": "ID",
        "username": "Username",
        "created_at": "Created",
    }

    form_columns = ["username", "password", "password_confirm"]
    form_args = {
        "username": {"label": "Username"},
    }

    form_extra_fields = {
        "password": PasswordField("Password"),
        "password_confirm": PasswordField("Confirm password"),
    }

    can_view_details = True
    page_size = 25

    def create_form(self, obj: Any = None) -> Any:
        form = super().create_form(obj)
        form.password.validators = [
            validators.DataRequired(message="Password is required."),
        ]
        form.password_confirm.validators = [
            validators.DataRequired(),
            validators.EqualTo("password", message="Passwords do not match."),
        ]
        return form

    def edit_form(self, obj: Any = None) -> Any:
        form = super().edit_form(obj)
        form.password.validators = [validators.Optional()]
        form.password_confirm.validators = [
            validators.Optional(),
            validators.EqualTo("password", message="Passwords do not match."),
        ]
        return form

    def on_model_change(self, form: Any, model: Any, is_created: bool) -> None:
        if form.password.data:
            model.set_password(form.password.data)

    def delete_model(self, model: Any) -> Any:
        if model.id == current_user.id:
            flash("Cannot delete the current user.", "error")
            return False
        return super().delete_model(model)


class CityAdmin(SecureModelView):
    column_list = [
        "id",
        "name",
        "latitude",
        "longitude",
        "check_interval_minutes",
        "last_checked_at",
        "created_at",
    ]
    column_searchable_list = ["name"]
    column_filters = ["name"]
    column_sortable_list = ["id", "name", "created_at", "last_checked_at"]
    column_default_sort = ("id", False)

    column_labels = {
        "id": "ID",
        "name": "Name",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "check_interval_minutes": "Check interval (min)",
        "last_checked_at": "Last checked",
        "created_at": "Created",
    }

    form_columns = ["name", "latitude", "longitude", "check_interval_minutes"]
    form_args = {
        "name": {"label": "Name"},
        "latitude": {"label": "Latitude"},
        "longitude": {"label": "Longitude"},
        "check_interval_minutes": {"label": "Check interval (minutes)"},
    }

    can_view_details = True
    page_size = 25
    details_template = "admin/city_detail.html"

    @expose("/details/", methods=("GET",))
    def details_view(self) -> Any:
        return_url = self.get_url(".index_view")

        if not self.can_view_details:
            return redirect(return_url)

        city_id = get_mdict_item_or_list(request.args, "id")
        if city_id is None:
            return redirect(return_url)

        city = self.get_one(city_id)
        if city is None:
            flash("Record does not exist.", "error")
            return redirect(return_url)

        return self.render(
            self.details_template,
            model=city,
            return_url=return_url,
            **_city_weather_context(city),
        )

    @expose("/fetch-weather/", methods=["POST"])
    def fetch_weather_now(self) -> Response:
        from app.services.weather import WeatherFetchError, fetch_weather_for_city

        return_url = self.get_url(".index_view")
        city_id = get_mdict_item_or_list(request.args, "id")
        if city_id is None:
            flash("City not found.", "error")
            return redirect(return_url)

        city = db.session.get(City, int(city_id))
        if city is None:
            flash("City not found.", "error")
            return redirect(return_url)

        try:
            fetch_weather_for_city(city)
            flash("Weather data fetched.", "success")
        except WeatherFetchError as exc:
            flash(f"Failed to fetch weather: {exc}", "danger")

        return redirect(self.get_url(".details_view", id=city_id))


class WeatherRecordAdmin(SecureModelView):
    column_list = [
        "id",
        "city_id",
        "recorded_at",
        "temperature_c",
        "humidity_percent",
        "wind_speed_ms",
        "weather_code",
        "precipitation_mm",
    ]
    column_filters = ["city_id", "recorded_at"]
    column_sortable_list = ["id", "recorded_at", "temperature_c"]
    column_default_sort = ("recorded_at", True)

    column_labels = {
        "id": "ID",
        "city_id": "City",
        "recorded_at": "Recorded at",
        "temperature_c": "Temperature (°C)",
        "humidity_percent": "Humidity (%)",
        "wind_speed_ms": "Wind speed (m/s)",
        "weather_code": "Weather code",
        "precipitation_mm": "Precipitation (mm)",
    }

    can_create = False
    can_edit = False
    can_view_details = True
    page_size = 25


class AppSettingsAdmin(SecureModelView):
    column_list = ["id", "default_check_interval_minutes", "updated_at"]
    column_sortable_list = ["id", "default_check_interval_minutes", "updated_at"]
    column_default_sort = ("id", False)

    column_labels = {
        "id": "ID",
        "default_check_interval_minutes": "Default check interval (min)",
        "updated_at": "Updated",
    }

    form_columns = ["default_check_interval_minutes"]
    form_args = {
        "default_check_interval_minutes": {"label": "Default check interval (minutes)"},
    }

    can_create = False
    can_delete = False
    can_view_details = True
    page_size = 25


class ToolsAdmin(SecureBaseView):
    @expose("/")
    def index(self) -> Any:
        from app.models import City, User, WeatherRecord

        return self.render(
            "admin/tools.html",
            cities_count=City.query.count(),
            weather_records_count=WeatherRecord.query.count(),
            users_count=User.query.count(),
        )

    @expose("/fetch-weather/", methods=["POST"])
    def fetch_weather(self) -> Response:
        from app.services.weather import fetch_due_cities

        records = fetch_due_cities()
        flash(f"Fetched weather for {len(records)} cities.", "success")
        return redirect(url_for(".index"))

    @expose("/seed-users/", methods=["POST"])
    def seed_users(self) -> Response:
        from app.services.user_service import seed_admin_user

        category, message = seed_admin_user()
        flash(message, category)
        return redirect(url_for(".index"))

    @expose("/clear-users/", methods=["POST"])
    def clear_users(self) -> Response:
        from app.services.user_service import clear_users_table

        category, message = clear_users_table()
        flash(message, category)
        return redirect(url_for(".index"))
