from __future__ import annotations

from flask import redirect, request, url_for
from flask_admin import AdminIndexView, BaseView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from werkzeug.wrappers.response import Response


class SecureAdminIndexView(AdminIndexView):  # type: ignore[misc]
    def is_accessible(self) -> bool:
        return bool(current_user.is_authenticated)

    def inaccessible_callback(self, name: str, **kwargs: object) -> Response:
        return redirect(url_for("auth.login", next=request.url))


class SecureModelView(ModelView):  # type: ignore[misc]
    def is_accessible(self) -> bool:
        return bool(current_user.is_authenticated)

    def inaccessible_callback(self, name: str, **kwargs: object) -> Response:
        return redirect(url_for("auth.login", next=request.url))


class SecureBaseView(BaseView):  # type: ignore[misc]
    def is_accessible(self) -> bool:
        return bool(current_user.is_authenticated)

    def inaccessible_callback(self, name: str, **kwargs: object) -> Response:
        return redirect(url_for("auth.login", next=request.url))
