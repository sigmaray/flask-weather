"""Add weather source settings and OpenWeatherMap records table

Revision ID: 007_weather_sources_and_owm_records
Revises: 006_unique_city_observed_at
Create Date: 2026-07-02

"""

import sqlalchemy as sa
from alembic import op

revision = "007_weather_sources_and_owm_records"
down_revision = "006_unique_city_observed_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("openweathermap_api_key", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("enable_open_meteo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "enable_openweathermap",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("app_settings", "enable_open_meteo", server_default=None)
    op.alter_column("app_settings", "enable_openweathermap", server_default=None)

    op.create_table(
        "owm_weather_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("timezone_offset_sec", sa.Integer(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("feels_like_c", sa.Float(), nullable=True),
        sa.Column("temp_min_c", sa.Float(), nullable=True),
        sa.Column("temp_max_c", sa.Float(), nullable=True),
        sa.Column("humidity_percent", sa.Float(), nullable=True),
        sa.Column("pressure_mmhg", sa.Float(), nullable=True),
        sa.Column("wind_speed_ms", sa.Float(), nullable=True),
        sa.Column("wind_deg", sa.Float(), nullable=True),
        sa.Column("weather_id", sa.Integer(), nullable=True),
        sa.Column("weather_main", sa.String(length=64), nullable=True),
        sa.Column("weather_description", sa.String(length=120), nullable=True),
        sa.Column("visibility_m", sa.Float(), nullable=True),
        sa.Column("cloudiness_percent", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "city_id",
            "observed_at",
            name="uq_owm_weather_records_city_observed_at",
        ),
    )
    op.create_index(
        op.f("ix_owm_weather_records_city_id"),
        "owm_weather_records",
        ["city_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_owm_weather_records_recorded_at"),
        "owm_weather_records",
        ["recorded_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_owm_weather_records_recorded_at"), table_name="owm_weather_records")
    op.drop_index(op.f("ix_owm_weather_records_city_id"), table_name="owm_weather_records")
    op.drop_table("owm_weather_records")
    op.drop_column("app_settings", "enable_openweathermap")
    op.drop_column("app_settings", "enable_open_meteo")
    op.drop_column("app_settings", "openweathermap_api_key")
