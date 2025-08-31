# routes\favorites.py

from flask import Blueprint, request, redirect, url_for, session, flash, render_template
from models.favorites import add_favorite_to_user, remove_favorite_from_user, get_user_favorite_spaces
from models.space import get_space_by_id, get_popular_spaces_in_location
from bson import ObjectId
from datetime import datetime

favorites_bp = Blueprint('favorites', __name__, template_folder='../templates')

# --- FIX: Helper function to make data JSON-serializable for the session ---
def sanitize_for_session(data):
    """
    Recursively cleans data to ensure it can be stored in the Flask session.
    Converts ObjectId and datetime objects to strings.
    """
    if isinstance(data, list):
        return [sanitize_for_session(item) for item in data]
    if isinstance(data, dict):
        return {key: sanitize_for_session(value) for key, value in data.items()}
    if isinstance(data, ObjectId):
        return str(data)
    if isinstance(data, datetime):
        return data.isoformat()
    return data

def get_current_user_id():
    return session.get('user_id')

@favorites_bp.route('/favorites')
def show_favorites():
    user_id = get_current_user_id()
    if not user_id:
        flash('You need to be logged in to see your favorites.', 'warning')
        return redirect(url_for('auth.login'))

    favorite_spaces = get_user_favorite_spaces(user_id)
    # Suggestions are now popped after being sanitized, ensuring clean session data
    suggested_spaces = session.pop('suggested_spaces', None)

    return render_template('favorites.html', favorites=favorite_spaces, suggestions=suggested_spaces)

@favorites_bp.route('/favorite/add/<space_id>')
def add_favorite(space_id):
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('auth.login'))

    add_favorite_to_user(user_id, space_id)
    flash('Added to your favorites!', 'success')

    space = get_space_by_id(space_id)
    if space:
        suggestions_from_db = get_popular_spaces_in_location(space['location_city'], exclude_id=space_id)
        # --- FIX: Sanitize the suggestions before placing them in the session ---
        session['suggested_spaces'] = sanitize_for_session(suggestions_from_db)
        session['new_suggestions'] = True

    return redirect(request.referrer or url_for('space_filters.view_spaces'))

@favorites_bp.route('/favorite/remove/<space_id>')
def remove_favorite(space_id):
    user_id = get_current_user_id()
    if not user_id:
        return redirect(url_for('auth.login'))

    remove_favorite_from_user(user_id, space_id)
    flash('Removed from your favorites.', 'info')

    space = get_space_by_id(space_id)
    if space:
        suggestions_from_db = get_popular_spaces_in_location(space['location_city'], exclude_id=space_id)
        # --- FIX: Sanitize the suggestions here as well for consistency ---
        session['suggested_spaces'] = sanitize_for_session(suggestions_from_db)
        session['new_suggestions'] = True

    return redirect(request.referrer or url_for('favorites.show_favorites'))
