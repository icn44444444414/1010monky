"""Delad admin-grind for analytics/CRM-vyerna (samma session som chatt-adminen)."""
from functools import wraps

from flask import session, redirect, url_for, request


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('chat_admin'):
            return redirect(url_for('chat_blueprint.admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapper
