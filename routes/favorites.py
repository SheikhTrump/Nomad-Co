#routes\favorites.py

from flask import Blueprint, request, redirect, url_for, session, flash, render_template
from models.favorites import add_favorite_to_user, remove_favorite_from_user, get_user_favorite_spaces
from models.space import get_space_by_id, get_popular_spaces_in_location
from models.user import db
from bson.objectid import ObjectId

favorites_bp = Blueprint('favorites', __name__, template_folder='../templates')

def get_current_user():
    if 'user_id' in session:
        try:
            return db.users.find_one({'_id': ObjectId(session['user_id'])})
        except Exception:
            return None
    return None

@favorites_bp.route('/favorites')
def show_favorites():
    user = get_current_user()
    if not user:
        flash('You need to be logged in to see your favorites.', 'warning')
        return redirect(url_for('auth.login'))

    favorite_spaces = get_user_favorite_spaces(user['user_id'])
    suggested_spaces = session.pop('suggested_spaces', None)

    return render_template('favorites.html', favorites=favorite_spaces, suggestions=suggested_spaces)

@favorites_bp.route('/favorite/add/<space_id>')
def add_favorite(space_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    add_favorite_to_user(user['user_id'], space_id)
    flash('Added to your favorites!', 'success')

    space = get_space_by_id(space_id)
    if space:
        suggestions = get_popular_spaces_in_location(space['location_city'], exclude_id=space_id)
        session['suggested_spaces'] = suggestions
        session['new_suggestions'] = True

    return redirect(request.referrer or url_for('space_filters.view_spaces'))

@favorites_bp.route('/favorite/remove/<space_id>')
def remove_favorite(space_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    space = get_space_by_id(space_id)
    remove_favorite_from_user(user['user_id'], space_id)
    flash('Removed from your favorites.', 'info')

    if space:
        suggestions = get_popular_spaces_in_location(space['location_city'], exclude_id=space_id)
        session['suggested_spaces'] = suggestions
        session['new_suggestions'] = True

    return redirect(request.referrer or url_for('favorites.show_favorites'))
