#routes/reviews.py

# Ei file ta notun review submit korar page er logic ebong route handle kore.

import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId # String ID ke ObjectId te convert korar jonno import
from models.review import create_review
from models.space import spaces_collection # Space details pawar jonno import

# 'reviews' name e notun Blueprint toiri kora hocche.
reviews_bp = Blueprint('reviews', __name__, template_folder='../templates')

# Upload kora review er chobi gulo ei folder e save hobe.
UPLOAD_FOLDER = 'static/uploads/reviews'
# Shudhu ei file extension gulo allowed.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    """File name er extension ta allowed kina sheta check kore."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# '/review/new/<space_id>' URL er jonno ei function ta kaaj korbe. GET and POST request handle korbe.
@reviews_bp.route('/review/new/<space_id>', methods=['GET', 'POST'])
def submit_review(space_id):
    """Review submit korar form dekhabe ebong form er data process korbe."""

    # Prothome check korbe user login kora ache kina.
    if 'user_id' not in session: 
        flash('You must be logged in to leave a review.', 'danger')
        return redirect(url_for('auth.login'))

    # Jokhon user form ta fillup kore submit korbe (POST request).
    if request.method == 'POST':
        # Form theke rating ebong comment er value neya hocche.
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        user_id = session['user_id']
        # Session theke user er first name neya hocche. Na paile 'Anonymous' dekhabe.
        user_name = session.get('first_name', 'Anonymous') 
        
        photo_url = None
        # Jodi form e kono photo upload kora hoy.
        if 'photo' in request.files:
            file = request.files['photo']
            # Jodi file thake ebong allowed type er hoy.
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename) # Securityr jonno filename ta clean kora hocche.
                # Jodi upload folder na thake, tobe toiri kora hocche.
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path) # File ta server e save kora hocche.
                photo_url = f"/{save_path.replace('//', '/')}" # Database e save korar jonno URL path toiri.

        # Model theke create_review function call kore database e review ta save kora hocche.
        create_review(space_id, user_id, user_name, rating, comment, photo_url)
        flash('Your review has been submitted successfully!', 'success')
        # Review submit howar por user ke space list er page e pathiye deya hobe.
        return redirect(url_for('space_filters.view_spaces'))

    # Jokhon user prothom page ta load korbe (GET request).
    # Space er details fetch kora hocche jate page e space er naam/chobi dekhano jay.
    space = spaces_collection.find_one({'_id': ObjectId(space_id)})
    if not space:
        flash('Space not found.', 'danger')
        return redirect(url_for('space_filters.view_spaces'))

    # 'submit_review.html' template ta render kora hocche space er details shoho.
    return render_template('submit_review.html', space=space)
