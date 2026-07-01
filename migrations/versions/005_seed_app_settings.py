"""Seed default app settings row

Revision ID: 005_seed_app_settings
Revises: 004_weather_extended_fields
Create Date: 2026-07-01

"""

from datetime import datetime

from alembic import op
from sqlalchemy import text

revision = "005_seed_app_settings"
down_revision = "004_weather_extended_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(text("SELECT 1 FROM app_settings WHERE id = 1")).fetchone()
    if exists is None:
        conn.execute(
            text(
                "INSERT INTO app_settings (id, default_check_interval_minutes, updated_at) "
                "VALUES (1, 1, :updated_at)"
            ),
            {"updated_at": datetime.utcnow()},
        )


def downgrade() -> None:
    op.execute(text("DELETE FROM app_settings WHERE id = 1"))
