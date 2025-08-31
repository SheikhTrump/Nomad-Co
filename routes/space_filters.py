#routes\space_filters.py
# Ei file ta shob space dekhano ebong filter korar page er jonno route handle kore.

from flask import Blueprint, render_template, request, session
# Model theke proyojonio function gulo import kora hocche.
from models.space import filter_spaces, add_sample_spaces
from models.review import get_average_rating_for_space
from models.favorites import get_user_favorite_ids
from models.traveler_profile import get_user_profile

# 'space_filters' name e ekta notun Blueprint toiri kora hocche.
space_filters_bp = Blueprint('space_filters', __name__, template_folder='../templates')

# '/spaces' URL er jonno ei function ta kaaj korbe, shudhu GET request handle korbe.
@space_filters_bp.route('/spaces', methods=['GET'])
def view_spaces():
    # Demonstration er jonno database e kichu sample space add kora hocche.
    # Ei function ta check kore jodi space na thake shudhu tokhoni add kore.
    add_sample_spaces()
    
    # Jodi user login kora thake, tar profile data fetch kora hocche 'best match' sorting er jonno.
    user_profile = None
    if 'user_id' in session:
        user_profile = get_user_profile(session['user_id'])

    # URL theke shob filter criteria (jemon min_price, location) neya hocche.
    # request.args.get diye query parameter (e.g., ?location=Dhaka) theke data neya hoy.
    filters = {
        'min_price': request.args.get('min_price', ''),
        'max_price': request.args.get('max_price', ''),
        'location': request.args.get('location', ''),
        'coworking': request.args.get('coworking', ''),
        'space_type': request.args.get('space_type', ''),
        'amenities': request.args.getlist('amenities'), # getlist use kora hoy multiple value pawar jonno (e.g., amenities=AC&amenities=WiFi)
        'sort_by': request.args.get('sort_by', 'best_match')
    }
    
    # Ei filter criteria gulo diye model er filter_spaces function call kore database theke space khuje ber kora hocche.
    spaces = filter_spaces(filters, user_profile)
    
    # Filter kora prottekta space er jonno average rating ber kora hocche.
    for space in spaces:
        # Rating hishab korar function call kora hocche.
        avg_rating, review_count = get_average_rating_for_space(space['_id'])
        # Space er dictionary te notun rating info add kora hocche.
        space['average_rating'] = avg_rating
        space['review_count'] = review_count

    # Current user er kon kon space favorite kora ache, shegular ID list ber kora hocche.
    favorite_ids = []
    if 'user_id' in session:
        favorite_ids = get_user_favorite_ids(session['user_id'])

    # Filter form e dekhanor jonno shob possible amenities er ekta list toiri kora.
    all_amenities = ["High-Speed WiFi", "AC", "Kitchen", "Parking"]
    
    # 'spaces.html' template ta render kora hocche ebong shob proyojonio data (spaces, filters, etc.) pass kora hocche.
    return render_template('spaces.html', spaces=spaces, filters=filters, all_amenities=all_amenities, favorites=favorite_ids)
