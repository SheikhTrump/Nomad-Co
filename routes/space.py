from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
from models.space import create_space as create_space_in_db, get_all_spaces



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
    # Only hosts can create spaces
    if session.get('role') != 'host':
        return redirect(url_for('auth.dashboard'))

    if request.method == 'GET':
        return render_template("create_space_form.html")

    # POST method logic...
    price_str = request.form.get("price_per_night")
    latitude_str = request.form.get("latitude")
    longitude_str = request.form.get("longitude")

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
        "host_id": session.get('user_id'),
        "host_name": session.get('first_name'),
        "space_title": request.form.get("space_title"),
        "description": request.form.get("description"),
        "price_per_night": price,
        "amenities": request.form.getlist("amenities"),
        "photos": photos_urls,
        "location": {"latitude": latitude, "longitude": longitude},
        "location_city": request.form.get("location_city") # Assuming a city field is added to the form
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
    return jsonify(spaces)


@space_bp.route("/create_space_form", methods=["GET"])
def create_space_form():
    return render_template("create_space_form.html")
