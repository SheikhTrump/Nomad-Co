# routes/space.py
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
from models.space import create_space as create_space_in_db

# The blueprint name is now 'space_bp' to match the new file
space_bp = Blueprint('space_bp', __name__)
upload_folder = 'static/uploads'

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
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            photos_urls.append(filepath)

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
    return jsonify({"message": "Space created", "id": str(result.inserted_id)})

# The conflicting '/spaces' route has been removed from this file.
# Bipresh's space_filters.py will handle the main '/spaces' page.
