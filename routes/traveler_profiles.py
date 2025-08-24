import os
import re
from flask import Blueprint, current_app, request, redirect, url_for, flash, session, render_template, jsonify
from werkzeug.utils import secure_filename
from models.space import cancel_booking_in_space
from models.traveler_profile import (
    get_booking_history,
    cancel_booking_history,
    get_user_profile,
    update_traveler_profile_info,
    get_emergency_contacts,
    update_emergency_contacts
)
from bson.objectid import ObjectId

#Traveler profile related routes er jonno blueprint create
traveler_profiles_bp = Blueprint('traveler_profiles', __name__, template_folder='../templates', static_folder='../static')

#File upload er settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#File er extension check korar function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Traveler profile dekhano
@traveler_profiles_bp.route("/profile/traveler")
def view_traveler_profile():
    #Jodi login kora na thake ba role traveler na hoy
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Login kore traveler hishabe thakte hobe.', 'danger')
        return redirect(url_for('auth.login'))

    #User er profile data DB theke ana
    user_id = session['user_id']
    profile_data = get_user_profile(user_id)

    if not profile_data:
        flash('Profile data pawa jaini.', 'danger')
        return redirect(url_for('auth.logout'))

    #Template e data pathano
    return render_template('traveler_profile.html', profile=profile_data)

#Traveler profile update kora
@traveler_profiles_bp.route("/profile/update", methods=['POST'])
def update_profile():
    #Security check korar way
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    new_profile_pic_path = None

    #File upload handle kora
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)  #Safe filename
            save_path = os.path.join(UPLOAD_FOLDER, filename)  #Save location
            file.save(save_path)
            new_profile_pic_path = f"/{save_path.replace('//', '/')}"

    #Form data collect kora
    form_data = request.form.to_dict()

    try:
        #Model function diye profile update
        update_traveler_profile_info(user_id, form_data, new_profile_pic_path)
        flash('Profile successfully update hoyeche!', 'success')
    except Exception as e:
        flash(f'Profile update korte problem: {e}', 'danger')

    #Update howar por abar profile page e pathano
    return redirect(url_for('traveler_profiles.view_traveler_profile'))

@traveler_profiles_bp.route("/profile/emergency_contacts", methods=['GET', 'POST'])
def emergency_contacts():
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    if request.method == 'POST':
        # Expecting a list of contacts from the form
        contacts = []
        names = request.form.getlist('contact_name')
        phones = request.form.getlist('contact_phone')
        relations = request.form.getlist('contact_relation')
        for n, p, r in zip(names, phones, relations):
            if n and p:
                contacts.append({'name': n, 'phone': p, 'relation': r})
        update_emergency_contacts(user_id, contacts)
        flash('Emergency contacts updated!', 'success')
        return redirect(url_for('traveler_profiles.view_traveler_profile'))
    contacts = get_emergency_contacts(user_id)
    return render_template('emergency_contacts.html', contacts=contacts)

@traveler_profiles_bp.route("/profile/booking_history")
def booking_history():
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    history = get_booking_history(user_id)
    return render_template('booking_history.html', history=history)

def _extract_id_like(val):
    """Accept ObjectId, "ObjectId('...')" string, or plain string and return cleaned id or None."""
    if not val:
        return None
    # ObjectId instance
    try:
        from bson import ObjectId as _OID
        if isinstance(val, _OID):
            return str(val)
    except Exception:
        pass
    if not isinstance(val, str):
        return str(val)
    v = val.strip()
    # "ObjectId('...')" or similar
    if v.startswith("ObjectId("):
        try:
            return v.split("'", 2)[1]
        except Exception:
            return v
    return v

@traveler_profiles_bp.route('/profile/bookings/<booking_id>/cancel', methods=['POST', 'GET'])
def cancel_booking_profile(booking_id):
    # require traveller
    if 'user_id' not in session or session.get('role') != 'traveler':
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "Authentication required"}), 401
        flash('Please sign in as a traveller to cancel bookings.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    # allow booking_id from path, form, query or JSON body
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

    # try to cancel in both space document and user booking history
    space_ok = False
    user_ok = False
    try:
        space_ok = bool(cancel_booking_in_space(bid, user_id))
    except Exception as e:
        current_app.logger.exception("Error cancelling booking in space: %s", e)
        space_ok = False

    try:
        user_ok = bool(cancel_booking_history(bid, user_id))
    except Exception as e:
        current_app.logger.exception("Error cancelling booking in user history: %s", e)
        user_ok = False

    success = bool(space_ok or user_ok)
    msg = 'Booking cancelled.' if success else 'Booking not found or you are not authorized to cancel it.'

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": success, "message": msg})

    flash(msg, 'success' if success else 'warning')
    return redirect(url_for('traveler_profiles.booking_history'))
