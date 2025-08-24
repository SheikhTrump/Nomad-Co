#routes/space_filters.py

from flask import Blueprint, render_template, request
from models.space import filter_spaces, add_sample_spaces, get_all_spaces
from models.review import get_average_rating_for_space
import os

space_filters_bp = Blueprint('space_filters', __name__, template_folder='../templates')

def _normalize_space_obj(raw):
    """
    Accepts a dict in either form:
      - {'_id': ..., 'photos': [...], ...}
      - {'space': {...}, 'average_rating': ..., ...}
    Returns a single normalized dict with:
      - '_id' as str
      - 'photos' paths normalized for url_for('static', filename=...)
      - ensures 'space_title' exists
    """
    # if wrapped in a 'space' key, merge top-level metadata into inner dict
    if isinstance(raw, dict) and 'space' in raw and isinstance(raw['space'], dict):
        inner = raw['space'].copy()
        # preserve any top-level metadata like average_rating/review_count
        for k in ('average_rating', 'review_count'):
            if k in raw:
                inner[k] = raw[k]
        s = inner
    else:
        s = raw if isinstance(raw, dict) else {}

    # convert _id to string
    if s.get('_id') is not None:
        s['_id'] = str(s['_id'])

    # normalize photos to be usable with url_for('static', filename=...)
    photos = s.get('photos') or []
    normalized = []
    for p in photos:
        if not p:
            continue
        p2 = p.replace("\\", "/")
        # remove any leading "static/" so templates can call url_for('static', filename=...)
        if p2.startswith("static/"):
            p2 = p2[len("static/"):]
        # if stored as absolute path, take basename and put under uploads/
        if os.path.isabs(p2) or (':' in p2 and '/' in p2):
            p2 = os.path.basename(p2)
            p2 = f"uploads/{p2}"
        # ensure uploads/ prefix if it looks like a saved upload filename
        if not p2.startswith("uploads/") and '/' not in p2:
            p2 = f"uploads/{p2}"
        normalized.append(p2)
    s['photos'] = normalized

    # ensure a title key templates expect
    s.setdefault('space_title', s.get('space_title') or s.get('title') or s.get('name') or '')

    return s

#Ei function ta '/spaces' URL er jonno kaj korbe
@space_filters_bp.route('/spaces', methods=['GET'])
def view_spaces():    
    add_sample_spaces() #Jodi database khali thake, tahole sample data add korbe

    #URL theke user er deya shob filter criteria collect kora
    filters = {
        'min_price': request.args.get('min_price', ''),
        'max_price': request.args.get('max_price', ''),
        'location': request.args.get('location', ''),
        'coworking': request.args.get('coworking', ''),
        'space_type': request.args.get('space_type', ''),
        'amenities': request.args.getlist('amenities'),
        'sort_by': request.args.get('sort_by', 'best_match')
    }

    spaces = filter_spaces(filters) #Filter criteria gulo diye database theke space khuje ber kora

    normalized_spaces = []
    for raw in spaces:
        s = _normalize_space_obj(raw)

        # safe call to rating helper (it expects an id-like value)
        try:
            avg_rating, review_count = get_average_rating_for_space(s.get('_id'))
        except Exception:
            avg_rating, review_count = 0, 0

        s['average_rating'] = avg_rating #Space er data te notun rating info add kora
        s['review_count'] = review_count

        normalized_spaces.append(s)

    #HTML form e dekhanor jonno amenities er ekta list
    all_amenities = ["High-Speed WiFi", "Kitchen", "AC", "Gym", "Pool"]
    
    return render_template('spaces.html', spaces=normalized_spaces, filters=filters, all_amenities=all_amenities)
