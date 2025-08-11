# routes/api.py
# Ei file ta JavaScript er jonno data provide korbe (JSON format e).

from flask import Blueprint, jsonify
from bson.objectid import ObjectId
from models.space import get_space_by_id
from models.review import get_reviews_for_space, get_average_rating_for_space

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/space/<space_id>')
def space_details(space_id):
    """
    Ekta single space er shob details, rating, ebong review JSON format e return kore.
    """
    try:
        space = get_space_by_id(space_id)
        if not space:
            return jsonify({"error": "Space not found"}), 404

        reviews = get_reviews_for_space(space_id)
        avg_rating, review_count = get_average_rating_for_space(space_id)

        # ObjectId gulo string e convert kora hocche jate JSON e kono error na hoy
        space['_id'] = str(space['_id'])
        for review in reviews:
            review['_id'] = str(review['_id'])
            review['space_id'] = str(review['space_id'])

        return jsonify({
            "space": space,
            "reviews": reviews,
            "average_rating": avg_rating,
            "review_count": review_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
