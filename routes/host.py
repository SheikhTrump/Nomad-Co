import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from models.space import create_space, get_spaces_by_host

host_profiles_bp = Blueprint("host_profiles", __name__, url_prefix="/host")

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@host_profiles_bp.route("/create", methods=["GET", "POST"])
def create_host_profile():
    if "user_id" not in session:
        flash("Please log in as a host to create a profile.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price_per_month = float(request.form["price_per_month"])
        amenities = request.form.getlist("amenities")
        space_type = request.form["space_type"]
        has_coworking_space = request.form.get("has_coworking_space") == "on"

        # Google Maps Coordinates
        location_city = request.form["location_city"]
        latitude = request.form["latitude"]
        longitude = request.form["longitude"]

        # Photo uploads
        photos = []
        if "photos" in request.files:
            files = request.files.getlist("photos")
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    photos.append(filename)

        # Save to MongoDB
        create_space(
            host_id=session["user_id"],
            name=name,
            description=description,
            price_per_month=price_per_month,
            amenities=amenities,
            location_city=location_city,
            space_type=space_type,
            has_coworking_space=has_coworking_space,
            photos=photos,
            latitude=latitude,
            longitude=longitude
        )

        flash("Host profile created successfully!", "success")
        return redirect(url_for("host_profiles.my_spaces"))

    return render_template("host_profile.html")

@host_profiles_bp.route("/my_spaces")
def my_spaces():
    if "user_id" not in session:
        flash("Please log in to view your spaces.", "danger")
        return redirect(url_for("auth.login"))

    spaces = get_spaces_by_host(session["user_id"])
    return render_template("my_spaces.html", spaces=spaces)
