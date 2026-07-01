"""Rename weather_records to om_weather_records

Revision ID: 008_rename_weather_records_to_om
Revises: 007_weather_sources_and_owm_records
Create Date: 2026-07-02

"""

from alembic import op

revision = "008_rename_weather_records_to_om"
down_revision = "007_weather_sources_and_owm_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("weather_records", "om_weather_records")
    op.execute(
        "ALTER INDEX ix_weather_records_city_id RENAME TO ix_om_weather_records_city_id"
    )
    op.execute(
        "ALTER INDEX ix_weather_records_recorded_at RENAME TO ix_om_weather_records_recorded_at"
    )
    op.execute(
        "ALTER TABLE om_weather_records RENAME CONSTRAINT "
        "uq_weather_records_city_observed_at TO uq_om_weather_records_city_observed_at"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE om_weather_records RENAME CONSTRAINT "
        "uq_om_weather_records_city_observed_at TO uq_weather_records_city_observed_at"
    )
    op.execute(
        "ALTER INDEX ix_om_weather_records_recorded_at RENAME TO ix_weather_records_recorded_at"
    )
    op.execute(
        "ALTER INDEX ix_om_weather_records_city_id RENAME TO ix_weather_records_city_id"
    )
    op.rename_table("om_weather_records", "weather_records")
