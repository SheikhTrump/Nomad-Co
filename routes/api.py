#routes/api.py
# Ei file ta shudhu data pathanor jonno toiri, kono HTML page dekhabe na.
# Ekhankar route gulo aamra JavaScript (AJAX/Fetch) theke call korbo JSON format e data pawar jonno.

from flask import Blueprint, jsonify
from bson.objectid import ObjectId
# Model theke proyojonio function gulo import kora hocche.
from models.space import get_space_by_id
from models.review import get_reviews_for_space, get_average_rating_for_space

# '/api' prefix diye ekta notun Blueprint toiri kora hocche.
api_bp = Blueprint('api', __name__, url_prefix='/api')

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

        # Database er ObjectId gulo JSON er jonno valid na, tai tader string e convert korte hoy.
        space['_id'] = str(space['_id'])
        for review in reviews:
            review['_id'] = str(review['_id'])
            review['space_id'] = str(review['space_id'])

        # Shob data ekta dictionary te shajiye JSON hishebe pathano hocche.
        return jsonify({
            "space": space,
            "reviews": reviews,
            "average_rating": avg_rating,
            "review_count": review_count
        })
    except Exception as e:
        # Jodi kono error hoy, tahole 500 server error pathano hocche.
        return jsonify({"error": str(e)}), 500
