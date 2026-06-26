from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import login_required

from app.extensions import db
from app.models import AppSettings

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def settings_page() -> ResponseReturnValue:
    app_settings = AppSettings.get_singleton()
    if request.method == "POST":
        interval_raw = request.form.get("default_check_interval_minutes", "").strip()
        try:
            interval = int(interval_raw)
            if interval < 1:
                raise ValueError
            app_settings.default_check_interval_minutes = interval
            db.session.commit()
            flash("Settings saved.", "success")
            return redirect(url_for("settings.settings_page"))
        except ValueError:
            flash("Default check interval must be a positive integer.", "danger")
    return render_template("settings/index.html", settings=app_settings)
