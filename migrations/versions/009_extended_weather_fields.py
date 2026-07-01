"""Add cloud cover for Open-Meteo and extra OWM weather fields

Revision ID: 009_extended_weather_fields
Revises: 008_rename_weather_records_to_om
Create Date: 2026-07-02

"""

import sqlalchemy as sa
from alembic import op

revision = "009_extended_weather_fields"
down_revision = "008_rename_weather_records_to_om"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "om_weather_records",
        sa.Column("cloudiness_percent", sa.Float(), nullable=True),
    )
    op.add_column(
        "owm_weather_records",
        sa.Column("dew_point_c", sa.Float(), nullable=True),
    )
    op.add_column(
        "owm_weather_records",
        sa.Column("uv_index", sa.Float(), nullable=True),
    )
    op.add_column(
        "owm_weather_records",
        sa.Column("precipitation_mm", sa.Float(), nullable=True),
    )
    op.add_column(
        "owm_weather_records",
        sa.Column("snow_1h_mm", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("owm_weather_records", "snow_1h_mm")
    op.drop_column("owm_weather_records", "precipitation_mm")
    op.drop_column("owm_weather_records", "uv_index")
    op.drop_column("owm_weather_records", "dew_point_c")
    op.drop_column("om_weather_records", "cloudiness_percent")
