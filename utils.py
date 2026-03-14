from functools import wraps
from flask import jsonify
from flask_login import current_user
import hashlib


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


def get_gravatar_url(email, size=128, default='identicon'):
    """
    Generate a Gravatar URL for the given email address.
    
    Args:
        email: User's email address
        size: Size of the avatar (default 128px)
        default: Default avatar style if no Gravatar exists (identicon, monsterid, wavatar, retro, robohash, blank)
    
    Returns:
        Gravatar URL string
    """
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d={default}"


def get_google_profile_picture(email, size=256):
    """
    Generate a profile picture URL based on user's Gmail account.
    This uses Google's public profile picture service.
    
    Args:
        email: User's email address (Gmail email)
        size: Size of the avatar
    
    Returns:
        URL string for the profile picture
    """
    # Try Google's contact photo service
    return f"https://lh3.googleusercontent.com/a/default-user={email}?sz={size}"


def get_ui_avatar_url(name, email, size=256, background='random'):
    """
    Generate a professional avatar using UI Avatars service based on user's name.
    This creates a nice colored avatar with the user's initials.
    
    Args:
        name: User's full name
        email: User's email (used for consistent color)
        size: Size of the avatar
        background: Background style (random, or specific color)
    
    Returns:
        URL string for the avatar
    """
    # Generate a consistent color based on email
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    color = email_hash[:6]  # Use first 6 chars of hash as color
    
    # URL encode the name for safe use in URL
    from urllib.parse import quote
    encoded_name = quote(name)
    
    return f"https://ui-avatars.com/api/?name={encoded_name}&size={size}&background={color}&color=fff&bold=true&font-size=0.4"


# Backwards-compatibility: export a name `login_required` that wraps Flask-Login behavior
# Use `api_login_required` for JSON APIs to avoid redirects.
login_required = api_login_required