from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
from models.space import create_space as create_space_in_db, get_all_spaces



space_bp = Blueprint('space_bp', __name__)
upload_folder = 'static/uploads'

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
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            photos_urls.append(filepath)

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
    return jsonify({"message": "Space created", "id": str(result.inserted_id)})

@space_bp.route("/spaces", methods=["GET"])
def get_spaces_route():
    spaces = get_all_spaces()
    return jsonify(spaces)


@space_bp.route("/create_space_form", methods=["GET"])
def create_space_form():
    return render_template("create_space_form.html")
