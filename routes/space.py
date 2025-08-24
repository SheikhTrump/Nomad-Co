from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
from bson import ObjectId
# add imports for new helpers
from models.space import create_space as create_space_in_db, get_all_spaces, get_space_by_id, add_booking_to_space, cancel_booking_in_space
from models.traveler_profile import add_booking_history, cancel_booking_history
from datetime import datetime
from flask import current_app

space_bp = Blueprint('space_bp', __name__)
upload_folder = 'static/uploads'

# ensure upload folder exists
os.makedirs(upload_folder, exist_ok=True)

# add helpers to normalize ids/space objects
def _normalize_incoming_id(val):
    """
    Accept common incoming id shapes and return a clean hex string id when possible.
    Handles ObjectId instances and strings like "ObjectId('...')".
    """
    if isinstance(val, ObjectId):
        return str(val)
    if not isinstance(val, str):
        return val
    v = val.strip()
    if v.startswith("ObjectId("):
        try:
            return v.split("'", 2)[1]
        except Exception:
            return v
    return v

def _unwrap_and_normalize_space_obj(raw):
    """
    Accept space dicts in variants (wrapped under 'space' key or direct).
    Ensures:
     - '_id' is a string
     - 'photos' paths are normalized for url_for('static', filename=...)
     - 'space_title' exists
    """
    if not isinstance(raw, dict):
        return raw
    s = raw.get('space').copy() if 'space' in raw and isinstance(raw['space'], dict) else raw.copy()

    # carry top-level metadata if wrapped
    for k in ('average_rating', 'review_count', 'reviews'):
        if k in raw and k not in s:
            s[k] = raw[k]

    # normalize id
    if s.get('_id') is not None:
        s['_id'] = str(s['_id'])

    # normalize photos
    photos = s.get('photos') or []
    normalized = []
    for p in photos:
        if not p:
            continue
        p2 = p.replace("\\", "/")
        if p2.startswith("static/"):
            p2 = p2[len("static/"):]
        if os.path.isabs(p2) or (':' in p2 and '/' in p2):
            p2 = os.path.basename(p2)
            p2 = f"uploads/{p2}"
        if not p2.startswith("uploads/") and '/' not in p2:
            p2 = f"uploads/{p2}"
        normalized.append(p2)
    s['photos'] = normalized

    s.setdefault('space_title', s.get('space_title') or s.get('title') or s.get('name') or '')
    return s

@space_bp.route('/spaces/create', methods=['GET', 'POST'])
def create_space():
    if request.method == 'GET':
        return render_template("create_space_form.html")

    # POST method
    price_str = request.form.get("price_per_night")
    latitude_str = request.form.get("latitude")
    longitude_str = request.form.get("longitude")

    # Validate required fields
    if not price_str or not latitude_str or not longitude_str:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        price = float(price_str)
        latitude = float(latitude_str)
        longitude = float(longitude_str)
    except ValueError:
        return jsonify({"error": "Invalid number format"}), 400

    photos_urls = []
    if "photos" in request.files:
        for file in request.files.getlist("photos"):
            filename = secure_filename(file.filename)
            if not filename:
                continue
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            # store relative path under static/uploads so templates can use url_for('static', filename=...)
            photos_urls.append(f"uploads/{filename}")

    space_data = {
        "space_title": request.form.get("space_title"),
        "description": request.form.get("description"),
        "price_per_night": price,
        "amenities": request.form.getlist("amenities"),
        "photos": photos_urls,
        "location": {
            "latitude": latitude,
            "longitude": longitude
        }
    }

    result = create_space_in_db(space_data)
    created_id = str(result.inserted_id)

    # API clients expect JSON
    if request.is_json or request.headers.get('Accept', '').lower().find('application/json') != -1:
        return jsonify({"message": "Space created", "id": created_id}), 201

    # Browser flow: flash and redirect to the spaces listing page so the user can see the new space
    flash("Space created", "success")
    return redirect(url_for('space_bp.list_spaces'))


@space_bp.route("/spaces", methods=["GET"])
def get_spaces_route():
    spaces = get_all_spaces()

    # Ensure API JSON still works
    if request.is_json or request.headers.get('Accept', '').lower().find('application/json') != -1:
        # for API clients, return raw spaces but add review_count for consistency
        for s in spaces:
            if isinstance(s, dict):
                # make IDs JSON-friendly
                if s.get('_id') is not None:
                    s['_id'] = str(s['_id'])
                s.setdefault('review_count', len(s.get('reviews') or []))
        return jsonify(spaces)

    # Build filters for template
    filters = {
        "location": request.args.get("location", ""),
        "min_price": request.args.get("min_price", ""),
        "max_price": request.args.get("max_price", ""),
        "amenities": request.args.getlist("amenities")
    }

    # Normalize spaces for template (ensure review_count and consistent title key)
    for s in spaces:
        if isinstance(s, dict):
            # convert ObjectId to string so url_for(...) in templates gets a clean value
            if s.get('_id') is not None:
                s['_id'] = str(s['_id'])
            s.setdefault('review_count', len(s.get('reviews') or []))
            s.setdefault('space_title', s.get('space_title') or s.get('title') or s.get('name') or '')

    all_amenities = sorted({
        amen
        for s in spaces
        for amen in (s.get("amenities") or [])
    })

    return render_template("spaces.html", spaces=spaces, filters=filters, all_amenities=all_amenities)


# new explicit route for HTML listing (used by redirects)
@space_bp.route("/spaces/list", methods=["GET"])
def list_spaces():
    spaces = get_all_spaces()

    # Normalize photo paths so templates can reliably call url_for('static', filename=...)
    import os
    for s in spaces:
        if isinstance(s, dict):
            # ensure ID is a string
            if s.get('_id') is not None:
                s['_id'] = str(s['_id'])

            photos = s.get("photos") or []
            normalized = []
            for p in photos:
                if not p:
                    continue
                # replace backslashes, remove leading "static/" or "static\\"
                p2 = p.replace("\\", "/")
                if p2.startswith("static/"):
                    p2 = p2[len("static/"):]
                # if absolute path, use basename
                if (os.path.isabs(p2) or ":" in p2) and "/" in p2:
                    p2 = os.path.basename(p2)
                    p2 = f"uploads/{p2}"
                normalized.append(p2)
            s['photos'] = normalized
            # also ensure space_title exists
            s.setdefault('space_title', s.get('space_title') or s.get('title') or s.get('name') or '')

    filters = {
        "location": request.args.get("location", ""),
        "min_price": request.args.get("min_price", ""),
        "max_price": request.args.get("max_price", ""),
        "amenities": request.args.getlist("amenities")
    }

    for s in spaces:
        if isinstance(s, dict):
            s.setdefault('review_count', len(s.get('reviews') or []))
            s.setdefault('space_title', s.get('space_title') or s.get('title') or s.get('name') or '')

    all_amenities = sorted({
        amen
        for s in spaces
        for amen in (s.get("amenities") or [])
    })

    return render_template("spaces.html", spaces=spaces, filters=filters, all_amenities=all_amenities)


@space_bp.route("/create_space_form", methods=["GET"])
def create_space_form():
    return render_template("create_space_form.html")

@space_bp.route('/<space_id>/book', methods=['GET', 'POST'])
def book_space(space_id):
    # only travellers can book
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Please sign in as a traveller to book.', 'warning')
        return redirect(url_for('auth.login'))

    # normalize incoming id before lookup (handles ObjectId('...') string shapes)
    clean_id = _normalize_incoming_id(space_id)
    space = get_space_by_id(clean_id)
    if not space:
        flash('Space not found.', 'danger')
        return redirect(url_for('space_bp.list_spaces'))

    # unwrap/normalize any wrapped space object and ensure string id present
    space = _unwrap_and_normalize_space_obj(space)
    if isinstance(space, dict) and (space.get('_id') is None or space.get('_id') == ''):
        space['_id'] = str(clean_id)

    if request.method == 'POST':
        user_id = session['user_id']
        date = request.form.get('date')
        guests = request.form.get('guests') or None

        # create a stable booking_id so cancel can address this booking
        booking_id = str(ObjectId())

        booking = {
            'booking_id': booking_id,
            'user_id': user_id,
            'space_id': str(clean_id),
            'space_title': space.get('space_title') or '',
            'date': date,
            'guests': int(guests) if guests else None,
            'status': 'Confirmed',
            'created_at': datetime.utcnow()
        }

        # store booking both on space and on the user's booking history
        add_booking_to_space(clean_id, booking)
        add_booking_history(user_id, {
            'booking_id': booking_id,
            'space_id': booking['space_id'],
            'space_title': booking['space_title'],
            'date': booking['date'],
            'status': booking['status'],
            'created_at': booking['created_at']
        })

        flash('Booking confirmed.', 'success')
        return redirect(url_for('traveler_profiles.view_traveler_profile'))

    # GET -> show small booking form
    return render_template('booking_form.html', space=space)

@space_bp.route('/<space_id>')
def space_detail(space_id):
    clean_id = _normalize_incoming_id(space_id)
    space = get_space_by_id(clean_id)
    if not space:
        return jsonify({"error": "Space not found"}), 404

    # unwrap/normalize space object for templates
    space = _unwrap_and_normalize_space_obj(space)
    if isinstance(space, dict) and (space.get('_id') is None or space.get('_id') == ''):
        space['_id'] = str(clean_id)

    # Normalize keys used by templates
    if isinstance(space, dict):
        space.setdefault('space_title', space.get('space_title') or space.get('title') or space.get('name') or '')
        space.setdefault('photos', space.get('photos') or [])
        space.setdefault('amenities', space.get('amenities') or [])
        space.setdefault('price_per_night', space.get('price_per_night') or 0)
        space.setdefault('description', space.get('description') or '')

    # Return JSON for API clients
    if request.is_json or request.headers.get('Accept', '').lower().find('application/json') != -1:
        return jsonify(space)

    # Browser -> render an HTML detail page with a Book button
    return render_template('space_detail.html', space=space)

def _extract_id_like(val):
    """
    Accepts ObjectId, "ObjectId('...')" string, or plain string and returns a clean id string or None.
    """
    if not val:
        return None
    if isinstance(val, ObjectId):
        return str(val)
    if not isinstance(val, str):
        return val
    v = val.strip()
    if v.startswith("ObjectId("):
        try:
            return v.split("'", 2)[1]
        except Exception:
            return v
    return v

@space_bp.route('/bookings/<booking_id>/cancel', methods=['POST', 'GET'])
def cancel_booking(booking_id):
    # require traveller
    if 'user_id' not in session or session.get('role') != 'traveler':
        # respond appropriately for AJAX clients
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "Authentication required"}), 401
        flash('Please sign in as a traveller to cancel bookings.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    # allow booking_id from path, query, form or JSON body
    body = request.get_json(silent=True) or {}
    candidate = booking_id or request.form.get('booking_id') or request.args.get('booking_id') or body.get('booking_id')
    bid = _extract_id_like(candidate)

    current_app.logger.debug("Cancel booking called: booking_id=%s user_id=%s method=%s", bid, user_id, request.method)

    if not bid:
        msg = 'Invalid booking selected.'
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": msg}), 400
        flash(msg, 'warning')
        return redirect(url_for('traveler_profiles.booking_history'))

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
    if success:
        msg = 'Booking cancelled.'
    else:
        msg = 'Booking not found or you are not authorized to cancel it.'

    # JSON / AJAX response
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": success, "message": msg})

    # browser response
    flash(msg, 'success' if success else 'warning')
    return redirect(url_for('traveler_profiles.booking_history'))
