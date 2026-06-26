from __future__ import annotations

from flask import Blueprint, render_template
from flask.typing import ResponseReturnValue
from flask_login import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index() -> ResponseReturnValue:
    return render_template("main/index.html")
