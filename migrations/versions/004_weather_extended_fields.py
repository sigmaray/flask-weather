"""Add extended weather fields to weather records

Revision ID: 004_weather_extended_fields
Revises: 003_city_location_fields
Create Date: 2026-06-27

"""

import sqlalchemy as sa
from alembic import op

revision = "004_weather_extended_fields"
down_revision = "003_city_location_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("weather_records", sa.Column("dew_point_c", sa.Float(), nullable=True))
    op.add_column("weather_records", sa.Column("pressure_mmhg", sa.Float(), nullable=True))
    op.add_column(
        "weather_records", sa.Column("apparent_temperature_c", sa.Float(), nullable=True)
    )
    op.add_column("weather_records", sa.Column("uv_index", sa.Float(), nullable=True))
    op.add_column(
        "weather_records", sa.Column("observed_at_local", sa.DateTime(), nullable=True)
    )
    op.add_column("weather_records", sa.Column("timezone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("weather_records", "timezone")
    op.drop_column("weather_records", "observed_at_local")
    op.drop_column("weather_records", "uv_index")
    op.drop_column("weather_records", "apparent_temperature_c")
    op.drop_column("weather_records", "pressure_mmhg")
    op.drop_column("weather_records", "dew_point_c")
