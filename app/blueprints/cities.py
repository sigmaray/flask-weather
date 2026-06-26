from __future__ import annotations

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import login_required

from app.extensions import db
from app.models import AppSettings, City
from app.services.weather import WeatherFetchError, fetch_weather_for_city

cities_bp = Blueprint("cities", __name__, url_prefix="/cities")


@cities_bp.route("/")
@login_required
def list_cities() -> ResponseReturnValue:
    cities = City.query.order_by(City.name).all()
    default_interval = AppSettings.get_singleton().default_check_interval_minutes
    return render_template(
        "cities/list.html",
        cities=cities,
        default_interval=default_interval,
    )


@cities_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_city() -> ResponseReturnValue:
    default_interval = AppSettings.get_singleton().default_check_interval_minutes
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        interval_raw = request.form.get("check_interval_minutes", "").strip()

        errors: list[str] = []
        if not name:
            errors.append("Name is required.")
        try:
            lat = float(latitude)
            lon = float(longitude)
        except ValueError:
            errors.append("Latitude and longitude must be valid numbers.")

        interval: int | None = None
        if interval_raw:
            try:
                interval = int(interval_raw)
                if interval < 1:
                    errors.append("Check interval must be at least 1 minute.")
            except ValueError:
                errors.append("Check interval must be an integer.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            city = City(
                name=name,
                latitude=lat,
                longitude=lon,
                check_interval_minutes=interval,
            )
            db.session.add(city)
            db.session.commit()
            flash(f"City {name!r} added.", "success")
            return redirect(url_for("cities.list_cities"))

    return render_template("cities/add.html", default_interval=default_interval)


@cities_bp.route("/<int:city_id>")
@login_required
def city_detail(city_id: int) -> ResponseReturnValue:
    city = db.get_or_404(City, city_id)
    records = list(city.weather_records)[:100]
    chart_data = {
        "labels": [r.recorded_at.strftime("%Y-%m-%d %H:%M") for r in reversed(records)],
        "temperatures": [r.temperature_c for r in reversed(records)],
        "humidity": [r.humidity_percent for r in reversed(records)],
        "wind": [r.wind_speed_ms for r in reversed(records)],
    }
    return render_template(
        "cities/detail.html",
        city=city,
        records=records,
        chart_data_json=json.dumps(chart_data),
        default_interval=AppSettings.get_singleton().default_check_interval_minutes,
    )


@cities_bp.route("/<int:city_id>/fetch", methods=["POST"])
@login_required
def fetch_now(city_id: int) -> ResponseReturnValue:
    city = db.get_or_404(City, city_id)
    try:
        fetch_weather_for_city(city)
        flash("Weather data fetched.", "success")
    except WeatherFetchError as exc:
        flash(f"Failed to fetch weather: {exc}", "danger")
    return redirect(url_for("cities.city_detail", city_id=city_id))
