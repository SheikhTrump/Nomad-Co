#routes/reviews.py

#Ei file ta review submit korar page er logic handle korbe.

import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId #ObjectId import kora dorkar eitateo
from models.review import create_review
from models.space import spaces_collection #Space details pawar jonno

reviews_bp = Blueprint('reviews', __name__, template_folder='../templates')

#Uploaded review er chobi gulo ei folder e save hobe
UPLOAD_FOLDER = 'static/uploads/reviews'
#Shudhu ei type er file upload kora jabe
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@reviews_bp.route('/review/new/<space_id>', methods=['GET', 'POST'])
def submit_review(space_id):
    #Review submit korar form dekhabe ebong form submission handle korbe

    if 'user_id' not in session: #User login kora ache kina check korbe
        flash('You must be logged in to leave a review.', 'danger')
        return redirect(url_for('auth.login'))

    #User jokhon form submit korbe (POST request)
    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        user_id = session['user_id']
        #Session theke user er naam nibe
        user_name = session.get('first_name', 'Anonymous')
        
        photo_url = None
        #Photo upload handle korar logic
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                #Upload folder ta exist na korle toiri korbe
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                photo_url = f"/{save_path.replace('//', '/')}"

        #Database e review save korar jonno function call korbe
        create_review(space_id, user_id, user_name, rating, comment, photo_url)
        flash('Your review has been submitted successfully!', 'success')
        #Review dewar por spaces page e redirect korbe
        return redirect(url_for('space_filters.view_spaces'))

    #User jokhon prothom page ta load korbe (GET request)
    space = spaces_collection.find_one({'_id': ObjectId(space_id)})
    if not space:
        flash('Space not found.', 'danger')
        return redirect(url_for('space_filters.view_spaces'))

    return render_template('submit_review.html', space=space)
