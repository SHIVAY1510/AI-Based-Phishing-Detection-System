from functools import wraps
from flask import jsonify
from flask_login import current_user


def api_login_required(func):
    """Decorator for API endpoints that returns JSON 401 instead of redirecting."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(current_user, 'is_authenticated', False):
            return jsonify({'error': 'Unauthorized: Please log in to access this resource.'}), 401
        return func(*args, **kwargs)

    return wrapper


def get_current_user_id():
    """Return the current user's id or None."""
    return getattr(current_user, 'id', None)


# Backwards-compatibility: export a name `login_required` that wraps Flask-Login behavior
# Use `api_login_required` for JSON APIs to avoid redirects.
login_required = api_login_required