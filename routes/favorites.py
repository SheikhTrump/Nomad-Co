# routes/favorites.py
from flask import Blueprint, request, redirect, url_for, session, flash, render_template
from models.favorites import add_favorite_to_user, remove_favorite_from_user, get_user_favorite_spaces

favorites_bp = Blueprint('favorites', __name__, template_folder='../templates')

@favorites_bp.route('/favorites')
def show_favorites():
    if 'user_id' not in session:
        flash('You need to be logged in to see your favorites.', 'warning')
        return redirect(url_for('auth.login'))
    favorite_spaces = get_user_favorite_spaces(session['user_id'])
    return render_template('favorites.html', favorites=favorite_spaces)

@favorites_bp.route('/favorite/add/<space_id>')
def add_favorite(space_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    add_favorite_to_user(session['user_id'], space_id)
    flash('Added to your favorites!', 'success')
    return redirect(request.referrer or url_for('space_filters.view_spaces'))

@favorites_bp.route('/favorite/remove/<space_id>')
def remove_favorite(space_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    remove_favorite_from_user(session['user_id'], space_id)
    flash('Removed from your favorites.', 'info')
    return redirect(request.referrer or url_for('space_filters.view_spaces'))
