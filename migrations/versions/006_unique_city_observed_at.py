"""Unique weather record per city and observed_at_local

Revision ID: 006_unique_city_observed_at
Revises: 005_seed_app_settings
Create Date: 2026-07-01

"""

from alembic import op
from sqlalchemy import text

revision = "006_unique_city_observed_at"
down_revision = "005_seed_app_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")

    op.execute(
        text(
            """
            DELETE FROM weather_records w1
            USING weather_records w2
            WHERE w1.observed_at_local IS NOT NULL
              AND w1.city_id = w2.city_id
              AND w1.observed_at_local = w2.observed_at_local
              AND w1.id > w2.id
            """
        )
    )
    op.create_unique_constraint(
        "uq_weather_records_city_observed_at",
        "weather_records",
        ["city_id", "observed_at_local"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_weather_records_city_observed_at",
        "weather_records",
        type_="unique",
    )
