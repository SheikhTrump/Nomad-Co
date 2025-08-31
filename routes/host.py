# routes\host.py

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from models.space import create_space_from_args, get_spaces_by_host
from models.user import submit_verification_photos, db
from bson.objectid import ObjectId

host_bp = Blueprint("host_profiles", __name__, url_prefix="/host")

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file):
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filepath

@host_bp.route("/create", methods=["GET", "POST"])
def create_host_profile():
    if "user_id" not in session:
        flash("Please log in as a host to create a space.", "danger")
        return redirect(url_for("auth.login"))
    try:
        user = db.users.find_one({'_id': ObjectId(session['user_id'])})
    except Exception:
        flash("Invalid user session. Please log in again.", "danger")
        return redirect(url_for("auth.login"))
    # Check verification status
    if not user or user.get('verification', {}).get('status') != 'approved':
        flash("You must be verified by admin before creating a space.", "warning")
        return redirect(url_for("auth.dashboard"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price_per_month = float(request.form["price_per_month"])
        amenities = request.form.getlist("amenities")
        space_type = request.form["space_type"]
        has_coworking_space = request.form.get("has_coworking_space") == "on"

        location_city = request.form["location_city"]
        latitude = request.form["latitude"]
        longitude = request.form["longitude"]

        photos = []
        if "photos" in request.files:
            files = request.files.getlist("photos")
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    photos.append(filepath)  

        
        create_space_from_args(
            session["user_id"],
            name,
            description,
            price_per_month,
            amenities,
            location_city,
            space_type,
            has_coworking_space,
            photos,
            latitude,
            longitude
        )

        flash("Space created successfully!", "success")
        return redirect(url_for("host_profiles.my_spaces"))

    return render_template("create_space_form.html")

@host_bp.route("/my_spaces")
def my_spaces():
    if "user_id" not in session:
        flash("Please log in to view your spaces.", "danger")
        return redirect(url_for("auth.login"))

    spaces = get_spaces_by_host(session["user_id"])
    return render_template("my_spaces.html", spaces=spaces)

@host_bp.route("/verify", methods=["POST"])
def verify_host():
    if "user_id" not in session or session.get("role") != "host":
        flash("Unauthorized.", "danger")
        return redirect(url_for("auth.dashboard"))
    nid_photo = request.files.get("nid_photo")
    own_photo = request.files.get("own_photo")
    if not nid_photo or not own_photo:
        flash("Both photos are required.", "danger")
        return redirect(url_for("auth.dashboard"))
    submit_verification_photos(session['user_id'], nid_photo, own_photo)
    flash("Verification submitted. Please wait for admin approval.", "info")
    return redirect(url_for("auth.dashboard"))
