#routes\space_filters.py

from flask import Blueprint, render_template, request, session
from models.space import filter_spaces, add_sample_spaces
from models.review import get_average_rating_for_space
from models.favorites import get_user_favorite_ids
from models.traveler_profile import get_user_profile

# Ei feature er jonno ekta notun Blueprint toiri kora
space_filters_bp = Blueprint('space_filters', __name__, template_folder='../templates')

# Ei function ta '/spaces' URL er jonno kaj korbe
@space_filters_bp.route('/spaces', methods=['GET'])
def view_spaces():
    # Add sample spaces to the database for demonstration
    add_sample_spaces()
    
    # Get user profile if a user is logged in
    user_profile = None
    if 'user_id' in session:
        user_profile = get_user_profile(session['user_id'])

    # Collect filter criteria from the request arguments
    filters = {
        'min_price': request.args.get('min_price', ''),
        'max_price': request.args.get('max_price', ''),
        'location': request.args.get('location', ''),
        'coworking': request.args.get('coworking', ''),
        'space_type': request.args.get('space_type', ''),
        'amenities': request.args.getlist('amenities'),
        'sort_by': request.args.get('sort_by', 'best_match')
    }
    
    # Filter criteria gulo diye database theke space khuje ber kora
    spaces = filter_spaces(filters, user_profile)
    
    # Prottekta space er jonno average rating ber kora
    for space in spaces:
        # Rating calculate korar function call kora
        avg_rating, review_count = get_average_rating_for_space(space['_id'])
        # Space er data te notun rating info add kora
        space['average_rating'] = avg_rating
        space['review_count'] = review_count

    # Get the list of favorite space IDs for the current user
    favorite_ids = []
    if 'user_id' in session:
        favorite_ids = get_user_favorite_ids(session['user_id'])

    # Define a list of all possible amenities for the filter form
    # FIXED: Cleaned up the amenities list as requested.
    all_amenities = ["High-Speed WiFi", "AC", "Kitchen", "Parking"]
    
    # Render the spaces page with the filtered spaces and other necessary data
    return render_template('spaces.html', spaces=spaces, filters=filters, all_amenities=all_amenities, favorites=favorite_ids)
