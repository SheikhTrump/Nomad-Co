# routes/space_filters.py
from flask import Blueprint, render_template, request, session
from models.space import filter_spaces, add_sample_spaces
from models.review import get_average_rating_for_space
from models.favorites import get_user_favorite_ids # <-- আপনার ফাংশনটি ইম্পোর্ট করুন

space_filters_bp = Blueprint('space_filters', __name__, template_folder='../templates')

@space_filters_bp.route('/spaces', methods=['GET'])
def view_spaces():
    add_sample_spaces()
    filters = {
        'min_price': request.args.get('min_price', ''),
        'max_price': request.args.get('max_price', ''),
        'location': request.args.get('location', ''),
        'coworking': request.args.get('coworking', ''),
        'space_type': request.args.get('space_type', ''),
        'amenities': request.args.getlist('amenities'),
        'sort_by': request.args.get('sort_by', 'best_match')
    }
    spaces = filter_spaces(filters)
    for space in spaces:
        avg_rating, review_count = get_average_rating_for_space(space['_id'])
        space['average_rating'] = avg_rating
        space['review_count'] = review_count

    # --- আপনার কোড এখানে যোগ করা হয়েছে ---
    favorite_ids = []
    if 'user_id' in session:
        favorite_ids = get_user_favorite_ids(session['user_id'])
    # --- আপনার কোড শেষ ---

    all_amenities = ["High-Speed WiFi", "Kitchen", "AC", "Gym", "Pool"]
    
    return render_template('spaces.html', spaces=spaces, filters=filters, all_amenities=all_amenities, favorites=favorite_ids)
