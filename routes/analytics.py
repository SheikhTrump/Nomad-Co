#routes\analytics.py
# Ei file ta admin er analytics dashboard page er jonno route define kore.

from flask import Blueprint, render_template, session, redirect, url_for, flash
# Model theke proyojonio function gulo import kora hocche.
from models.analytics import get_user_overview, get_booking_overview, get_recent_signups, get_recent_bookings, get_advanced_analytics
from bson.objectid import ObjectId # ObjectId ke string e convert korar jonno proyojon hote pare.

# 'analytics' name e ekta notun Blueprint toiri kora hocche.
analytics_bp = Blueprint('analytics', __name__, template_folder='../templates')

# '/analytics' URL er jonno ei function ta kaaj korbe.
@analytics_bp.route('/analytics')
def dashboard():
    """Admin der jonno main analytics dashboard ta display kore."""
    
    # Check kora hocche je user login kora kina ebong tar role 'admin' kina.
    if session.get('role') != 'admin':
        # Jodi admin na hoy, tahole permission nei shei message dekhano hobe.
        flash("You do not have permission to view this page.", "danger")
        # Onno ekta page e pathiye deya hobe.
        return redirect(url_for('auth.dashboard'))

    # Model theke bivinno analytics data fetch korar jonno function call kora hocche.
    user_data = get_user_overview()
    booking_data = get_booking_overview()
    advanced_data = get_advanced_analytics() # Notun advanced metrics gulo neya hocche.
    recent_users = get_recent_signups()
    recent_bookings = get_recent_bookings()

    # recent_users list er prottekta user er '_id' (jeta ekta ObjectId) ke string e convert kora hocche.
    # Eta na korle template e data dekhate giye error hote pare.
    for user in recent_users:
        user['_id'] = str(user['_id'])

    # 'analytics.html' template ta render kora hocche ebong shob fetch kora data pass kora hocche.
    return render_template(
        'analytics.html',
        user_data=user_data,
        booking_data=booking_data,
        advanced_data=advanced_data, # Notun data template e pathano hocche.
        recent_users=recent_users,
        recent_bookings=recent_bookings
    )

