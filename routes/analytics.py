#routes\analytics.py

from flask import Blueprint, render_template, session, redirect, url_for, flash
from models.analytics import get_user_overview, get_booking_overview, get_recent_signups, get_recent_bookings
from bson.objectid import ObjectId # Needed for processing recent signups

analytics_bp = Blueprint('analytics', __name__, template_folder='../templates')

@analytics_bp.route('/analytics')
def dashboard():
    """Displays the main analytics dashboard for admins."""
    if session.get('role') != 'admin':
        flash("You do not have permission to view this page.", "danger")
        return redirect(url_for('auth.dashboard'))

    user_data = get_user_overview()
    booking_data = get_booking_overview()
    recent_users = get_recent_signups()
    recent_bookings = get_recent_bookings()

    # Convert ObjectId to string for recent users to avoid template errors
    for user in recent_users:
        user['_id'] = str(user['_id'])

    return render_template(
        'analytics.html',
        user_data=user_data,
        booking_data=booking_data,
        recent_users=recent_users,
        recent_bookings=recent_bookings
    )
