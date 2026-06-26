from __future__ import annotations

import getpass

import click
from flask import Flask

from app.extensions import db
from app.models import User


def register_cli(app: Flask) -> None:
    @app.cli.command("create-user")
    @click.argument("username")
    def create_user(username: str) -> None:
        """Create a user (login only via CLI, not UI registration)."""
        username = username.strip()
        if not username:
            click.echo("Username cannot be empty.")
            raise SystemExit(1)

        if User.query.filter_by(username=username).first():
            click.echo(f"User {username!r} already exists.")
            raise SystemExit(1)

        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
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

    @app.cli.command("fetch-weather")
    def fetch_weather() -> None:
        """Fetch weather for all cities that are due."""
        from app.services.weather import fetch_due_cities

        records = fetch_due_cities()
        click.echo(f"Fetched weather for {len(records)} cities.")
