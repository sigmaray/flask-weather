from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"


class AppSettings(db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    default_check_interval_minutes = db.Column(db.Integer, nullable=False, default=1)
    openweathermap_api_key = db.Column(db.String(256), nullable=True)
    enable_open_meteo = db.Column(db.Boolean, nullable=False, default=True)
    enable_openweathermap = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    @classmethod
    def get_singleton(cls) -> AppSettings:
        settings = db.session.get(cls, 1)
        if settings is None:
            settings = cls(
                id=1,
                default_check_interval_minutes=1,
                enable_open_meteo=True,
                enable_openweathermap=False,
            )
            db.session.add(settings)
            db.session.commit()
        return settings


class City(db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    geocoded_name = db.Column(db.String(200), nullable=True)
    check_interval_minutes = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_checked_at = db.Column(db.DateTime, nullable=True)

    weather_records = db.relationship(
        "OmWeatherRecord",
        back_populates="city",
        cascade="all, delete-orphan",
        order_by="desc(OmWeatherRecord.recorded_at)",
    )
    owm_weather_records = db.relationship(
        "OwmWeatherRecord",
        back_populates="city",
        cascade="all, delete-orphan",
        order_by="desc(OwmWeatherRecord.recorded_at)",
    )

    def has_name_location(self) -> bool:
        return bool(self.name and self.country)

    def has_coordinate_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def display_name(self) -> str:
        if self.name and self.country:
            return f"{self.name}, {self.country}"
        if self.geocoded_name:
            return str(self.geocoded_name)
        if self.has_coordinate_location():
            return f"{self.latitude:.4f}, {self.longitude:.4f}"
        if self.name:
            return str(self.name)
        return "Unknown"

    def effective_interval_minutes(self) -> int:
        if self.check_interval_minutes is not None:
            return int(self.check_interval_minutes)
        return int(AppSettings.get_singleton().default_check_interval_minutes)

    def __repr__(self) -> str:
        return f"<City {self.display_name!r}>"


class OmWeatherRecord(db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "om_weather_records"
    __table_args__ = (
        db.UniqueConstraint(
            "city_id",
            "observed_at_local",
            name="uq_om_weather_records_city_observed_at",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=False, index=True)
    recorded_at = db.Column(db.DateTime, nullable=False, index=True)
    observed_at_local = db.Column(db.DateTime, nullable=True)
    timezone = db.Column(db.String(64), nullable=True)
    temperature_c = db.Column(db.Float, nullable=False)
    dew_point_c = db.Column(db.Float, nullable=True)
    humidity_percent = db.Column(db.Float, nullable=True)
    pressure_mmhg = db.Column(db.Float, nullable=True)
    wind_speed_ms = db.Column(db.Float, nullable=True)
    apparent_temperature_c = db.Column(db.Float, nullable=True)
    weather_code = db.Column(db.Integer, nullable=True)
    uv_index = db.Column(db.Float, nullable=True)
    precipitation_mm = db.Column(db.Float, nullable=True)
    snow_depth_m = db.Column(db.Float, nullable=True)
    cloudiness_percent = db.Column(db.Float, nullable=True)

    city = db.relationship("City", back_populates="weather_records")

    @property
    def display_time(self) -> datetime:
        return cast(datetime, self.observed_at_local or self.recorded_at)

    @property
    def observed_at_utc(self) -> datetime:
        if self.observed_at_local is not None and self.timezone:
            try:
                local_tz = ZoneInfo(self.timezone)
                local_aware = self.observed_at_local.replace(tzinfo=local_tz)
                return local_aware.astimezone(UTC).replace(tzinfo=None)
            except (KeyError, ValueError):
                pass
        return self.recorded_at

    @property
    def feels_like_c(self) -> float | None:
        return self.apparent_temperature_c

    @property
    def snow_depth_cm(self) -> float | None:
        if self.snow_depth_m is None:
            return None
        return self.snow_depth_m * 100

    def __repr__(self) -> str:
        return f"<OmWeatherRecord city_id={self.city_id} at {self.recorded_at}>"


class OwmWeatherRecord(db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "owm_weather_records"
    __table_args__ = (
        db.UniqueConstraint(
            "city_id",
            "observed_at",
            name="uq_owm_weather_records_city_observed_at",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=False, index=True)
    recorded_at = db.Column(db.DateTime, nullable=False, index=True)
    observed_at = db.Column(db.DateTime, nullable=False)
    timezone_offset_sec = db.Column(db.Integer, nullable=True)
    temperature_c = db.Column(db.Float, nullable=False)
    feels_like_c = db.Column(db.Float, nullable=True)
    temp_min_c = db.Column(db.Float, nullable=True)
    temp_max_c = db.Column(db.Float, nullable=True)
    humidity_percent = db.Column(db.Float, nullable=True)
    pressure_mmhg = db.Column(db.Float, nullable=True)
    wind_speed_ms = db.Column(db.Float, nullable=True)
    wind_deg = db.Column(db.Float, nullable=True)
    weather_id = db.Column(db.Integer, nullable=True)
    weather_main = db.Column(db.String(64), nullable=True)
    weather_description = db.Column(db.String(120), nullable=True)
    visibility_m = db.Column(db.Float, nullable=True)
    cloudiness_percent = db.Column(db.Float, nullable=True)
    precipitation_mm = db.Column(db.Float, nullable=True)
    snow_1h_mm = db.Column(db.Float, nullable=True)

    city = db.relationship("City", back_populates="owm_weather_records")

    @property
    def display_time(self) -> datetime:
        return self.observed_at

    @property
    def observed_at_utc(self) -> datetime:
        return self.observed_at

    @property
    def observed_at_local(self) -> datetime | None:
        if self.timezone_offset_sec is None:
            return None
        return self.observed_at + timedelta(seconds=self.timezone_offset_sec)

    @property
    def snow_depth_cm(self) -> float | None:
        return self.snow_1h_mm

    def __repr__(self) -> str:
        return f"<OwmWeatherRecord city_id={self.city_id} at {self.recorded_at}>"
