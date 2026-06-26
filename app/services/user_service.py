from __future__ import annotations

from app.extensions import db
from app.models import User

SEED_USERNAME = "admin"
SEED_PASSWORD = "admin"


def seed_admin_user() -> tuple[str, str]:
    """Create the default admin user if the database has no users."""
    if User.query.count() > 0:
        return ("info", f"User {SEED_USERNAME!r} already exists.")

    user = User(username=SEED_USERNAME)
    user.set_password(SEED_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return (
        "success",
        f"Test user created: login={SEED_USERNAME!r}, password={SEED_PASSWORD!r}",
    )


def clear_users_table() -> tuple[str, str]:
    """Delete all users. Returns (flash category, message)."""
    count = User.query.count()
    if count == 0:
        return ("info", "No users to delete.")

    User.query.delete()
    db.session.commit()
    return ("success", f"Deleted {count} user(s).")
