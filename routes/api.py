# routes/api.py
# Ei file ta shudhu data pathanor jonno toiri, kono HTML page dekhabe na.
# Ekhankar route gulo aamra JavaScript (AJAX/Fetch) theke call korbo JSON format e data pawar jonno.

from flask import Blueprint, jsonify
from bson.objectid import ObjectId
from datetime import datetime
# Model theke proyojonio function gulo import kora hocche.
from models.space import get_space_by_id
from models.review import get_reviews_for_space, get_average_rating_for_space

# '/api' prefix diye ekta notun Blueprint toiri kora hocche.
api_bp = Blueprint('api', __name__, url_prefix='/api')

def sanitize_for_json(data):
    """
    Recursively traverses a data structure (dict or list) and converts
    any BSON types (like ObjectId and datetime) to JSON-serializable formats.
    """
    if isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    if isinstance(data, dict):
        return {key: sanitize_for_json(value) for key, value in data.items()}
    if isinstance(data, ObjectId):
        return str(data)
    if isinstance(data, datetime):
        return data.isoformat()
    return data

# '/api/space/<space_id>' URL er jonno ei function ta kaaj korbe.
@api_bp.route('/space/<space_id>')
def space_details(space_id):
    """
    Ekta nirdishto space er shob details, rating, ebong review JSON format e return kore.
    """
    try:
        # Model theke space er details fetch kora hocche.
        space = get_space_by_id(space_id)
        if not space:
            # Jodi space na paowa jay, tahole 404 error pathano hocche.
            return jsonify({"error": "Space not found"}), 404

        # Oi space er shob review ebong average rating fetch kora hocche.
        reviews = get_reviews_for_space(space_id)
        avg_rating, review_count = get_average_rating_for_space(space_id)

        # CORRECTED: Use the robust sanitization function to clean all data
        clean_space = sanitize_for_json(space)
        clean_reviews = sanitize_for_json(reviews)

        # Shob data ekta dictionary te shajiye JSON hishebe pathano hocche.
        return jsonify({
            "space": clean_space,
            "reviews": clean_reviews,
            "average_rating": avg_rating,
            "review_count": review_count
        })
    except Exception as e:
        # Jodi kono error hoy, tahole 500 server error pathano hocche.
        return jsonify({"error": str(e)}), 500

