#routes\suggestions.py

from flask import Blueprint, render_template, session, redirect, url_for, flash

suggestions_bp = Blueprint('suggestions', __name__, template_folder='../templates')

@suggestions_bp.route('/suggestions')
def view_suggestions():
    """
    Displays the dedicated page for popular nearby spots.
    """
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('You must be logged in as a traveler to view suggestions.', 'danger')
        return redirect(url_for('auth.login'))

    # Get the suggestions from the session without removing them
    suggested_spaces = session.get('suggested_spaces', [])

    # After viewing, set the new_suggestions flag to false to stop the blinking
    session['new_suggestions'] = False

    return render_template('suggestions.html', suggestions=suggested_spaces)
