from __future__ import annotations

import click
from flask import Flask

from app.extensions import db
from app.models import User

SEED_USERNAME = "admin"
SEED_PASSWORD = "admin"


def register_cli(app: Flask) -> None:
    @app.cli.command("create-user")
    def create_user() -> None:
        """Create a user (login only via CLI, not UI registration)."""
        username = click.prompt("Login", type=str).strip()
        if not username:
            click.echo("Login cannot be empty.")
            raise SystemExit(1)

        if User.query.filter_by(username=username).first():
            click.echo(f"User {username!r} already exists.")
            raise SystemExit(1)

        password = click.prompt("Password", hide_input=True)
        confirm = click.prompt("Confirm password", hide_input=True)
        if password != confirm:
            click.echo("Passwords do not match.")
            raise SystemExit(1)
        if not password:
            click.echo("Password cannot be empty.")
            raise SystemExit(1)

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User {username!r} created.")

    @app.cli.command("users-clear")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
    def users_clear(yes: bool) -> None:
        """Delete all users."""
        count = User.query.count()
        if count == 0:
            click.echo("No users to delete.")
            return

        if not yes and not click.confirm(f"Delete all {count} user(s)?"):
            click.echo("Aborted.")
            raise SystemExit(1)

        User.query.delete()
        db.session.commit()
        click.echo(f"Deleted {count} user(s).")

    @app.cli.command("users-seed")
    def users_seed() -> None:
        """Create a test user for local development (admin / admin)."""
        if User.query.count() > 0:
            click.echo(f"User {SEED_USERNAME!r} already exists.")
            return

        user = User(username=SEED_USERNAME)
        user.set_password(SEED_PASSWORD)
        db.session.add(user)
        db.session.commit()
        click.echo(
            f"Test user created: login={SEED_USERNAME!r}, password={SEED_PASSWORD!r}"
        )

    @app.cli.command("fetch-weather")
    def fetch_weather() -> None:
        """Fetch weather for all cities that are due."""
        from app.services.weather import fetch_due_cities

        records = fetch_due_cities()
        click.echo(f"Fetched weather for {len(records)} cities.")
