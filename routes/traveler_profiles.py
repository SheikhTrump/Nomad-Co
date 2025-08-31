

import os
import re
from flask import Blueprint, current_app, request, redirect, url_for, flash, session, render_template, jsonify
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId

# Bivinno model theke proyojonio function gulo import kora hocche.
from models.space import cancel_booking_in_space
from models.traveler_profile import (
    update_traveler_profile_info,
    get_user_profile,
    get_emergency_contacts,
    update_emergency_contacts
)
from models.favorites import get_user_favorite_spaces
from models.review import get_reviews_by_user
from models.user import db 

# 'traveler_profiles' name e ekta Blueprint toiri kora hocche.
traveler_profiles_bp = Blueprint('traveler_profiles', __name__, template_folder='../templates', static_folder='../static')

# File upload er jonno settings.
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """File extension check korar jonno helper function."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@traveler_profiles_bp.route("/profile/traveler")
def view_traveler_profile():
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('You must be logged in as a traveler to view this page.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = db.users.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        flash('Could not find your profile data.', 'danger')
        return redirect(url_for('auth.logout'))
    user_id = user['user_id']
    profile_data = get_user_profile(user_id)
    '''
    user_id = session['user_id']
    # Model theke profile data, favorite spaces, reviews, etc. fetch kora hocche.
    profile_data = get_user_profile(user_id)
    '''
    if not profile_data:
        flash('Could not find your profile data.', 'danger')
        return redirect(url_for('auth.logout'))
    

    favorite_spaces = get_user_favorite_spaces(user_id)
    my_reviews = get_reviews_by_user(user_id)
    booking_history_data = list(db.bookings.find({'user_id': user_id}))
    emergency_contacts_data = get_emergency_contacts(user_id)

    # 'traveler_profile.html' template ta shob data shoho render kora hocche.
    return render_template(
        'traveler_profile.html',
        profile=profile_data,
        favorites=favorite_spaces,
        reviews=my_reviews,
        history=booking_history_data,
        contacts=emergency_contacts_data
    )

@traveler_profiles_bp.route("/profile/update", methods=['POST'])
def update_profile():
    """Profile update korar form submission handle kore."""
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    # AJAX request kina check korche.
    is_ajax = 'application/json' in request.headers.get('Accept', '')

    user_id = session['user_id']
    new_profile_pic_path = None

    # Profile picture upload handle kora hocche.
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)
            new_profile_pic_path = f"/{save_path.replace('//', '/')}"

    form_data = request.form.to_dict()

    try:
        # Model function call kore database e data update kora hocche.
        update_traveler_profile_info(user_id, form_data, new_profile_pic_path)
        flash('Profile successfully updated!', 'success')
        if is_ajax:
            return jsonify({'success': True})
        return redirect(url_for('traveler_profiles.view_traveler_profile'))
    except Exception as e:
        flash(f'An error occurred while updating: {e}', 'danger')
        if is_ajax:
            return jsonify({'success': False, 'message': str(e)}), 500
        return redirect(url_for('traveler_profiles.view_traveler_profile'))

@traveler_profiles_bp.route("/profile/emergency_contacts", methods=['GET', 'POST'])
def emergency_contacts():
    """Emergency contact add/update korar page ebong logic."""
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    if request.method == 'POST':
        contacts = []
        # Form theke prottekta contact er name, phone, relation neya hocche.
        names = request.form.getlist('contact_name')
        phones = request.form.getlist('contact_phone')
        relations = request.form.getlist('contact_relation')
        for n, p, r in zip(names, phones, relations):
            if n and p: # Jodi naam ebong phone number deya thake.
                contacts.append({'name': n, 'phone': p, 'relation': r})
        # Database e update kora hocche.
        update_emergency_contacts(user_id, contacts)
        flash('Emergency contacts updated!', 'success')
        return redirect(url_for('traveler_profiles.view_traveler_profile'))
    
    # GET request er jonno, current contact gulo fetch kore form dekhano hocche.
    contacts = get_emergency_contacts(user_id)
    return render_template('emergency_contacts.html', contacts=contacts)

@traveler_profiles_bp.route("/profile/booking_history")
def booking_history():
    """User er shob booking er history dekhay."""
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    history = list(db.bookings.find({'user_id': user_id}))
    
    # Session theke suggested space (jodi thake) neya hocche.
    suggested_spaces = session.get('suggested_spaces', None)
    
    return render_template('booking_history.html', history=history, suggestions=suggested_spaces)

def _extract_id_like(val):
    """Bivinno format theke shudhu ID ta ber kore anar jonno helper function."""
    if not val:
        return None
    try:
        from bson import ObjectId as _OID
        if isinstance(val, _OID):
            return str(val)
    except Exception:
        pass
    if not isinstance(val, str):
        return str(val)
    v = val.strip()
    if v.startswith("ObjectId("):
        try:
            return v.split("'", 2)[1]
        except Exception:
            return v
    return v

@traveler_profiles_bp.route('/profile/bookings/<booking_id>/cancel', methods=['POST', 'GET'])
def cancel_booking_profile(booking_id):
    """Ekta booking cancel korar logic."""
    if 'user_id' not in session or session.get('role') != 'traveler':
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "Authentication required"}), 401
        flash('Please sign in as a traveller to cancel bookings.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    body = request.get_json(silent=True) or {}
    candidate = booking_id or request.form.get('booking_id') or request.args.get('booking_id') or body.get('booking_id')
    bid = _extract_id_like(candidate)

    current_app.logger.debug("cancel_booking_profile called: booking_id=%s user_id=%s method=%s", bid, user_id, request.method)

    if not bid:
        msg = 'Invalid booking selected.'
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, 'warning')
        return redirect(url_for('traveler_profiles.booking_history'))

    try:
        # Database e booking er status "Cancelled" e update kora hocche.
        result = db.bookings.update_one(
            {"booking_id": bid, "user_id": user_id}, # Shudhu ei user er booking e cancel korte parbe.
            {"$set": {"status": "Cancelled"}}
        )
        success = result.modified_count > 0 # Jodi ekta document o update hoy, tahole success.
    except Exception as e:
        current_app.logger.exception("Error cancelling booking: %s", e)
        success = False

    msg = 'Booking cancelled.' if success else 'Booking not found or you are not authorized to cancel it.'
    
    # Jodi AJAX request hoy, JSON response pathano hocche.
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": success, "message": msg})

    flash(msg, 'success' if success else 'warning')
    return redirect(url_for('traveler_profiles.booking_history'))

