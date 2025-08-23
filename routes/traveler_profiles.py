import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from models.traveler_profile import update_traveler_profile_info, get_user_profile

#Traveler profile related routes er jonno blueprint create
traveler_profiles_bp = Blueprint('traveler_profiles', __name__, template_folder='../templates', static_folder='../static')

#File upload er settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#File er extension check korar function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Traveler profile dekhano
@traveler_profiles_bp.route("/profile/traveler")
def view_traveler_profile():
    #Jodi login kora na thake ba role traveler na hoy
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Login kore traveler hishabe thakte hobe.', 'danger')
        return redirect(url_for('auth.login'))

    #User er profile data DB theke ana
    user_id = session['user_id']
    profile_data = get_user_profile(user_id)

    if not profile_data:
        flash('Profile data pawa jaini.', 'danger')
        return redirect(url_for('auth.logout'))

    #Template e data pathano
    return render_template('traveler_profile.html', profile=profile_data)

#Traveler profile update kora
@traveler_profiles_bp.route("/profile/update", methods=['POST'])
def update_profile():
    #Security check korar way
    if 'user_id' not in session or session.get('role') != 'traveler':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    new_profile_pic_path = None

    #File upload handle kora
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)  #Safe filename
            save_path = os.path.join(UPLOAD_FOLDER, filename)  #Save location
            file.save(save_path)
            new_profile_pic_path = f"/{save_path.replace('//', '/')}"

    #Form data collect kora
    form_data = request.form.to_dict()

    try:
        #Model function diye profile update
        update_traveler_profile_info(user_id, form_data, new_profile_pic_path)
        flash('Profile successfully update hoyeche!', 'success')
    except Exception as e:
        flash(f'Profile update korte problem: {e}', 'danger')

    #Update howar por abar profile page e pathano
    return redirect(url_for('traveler_profiles.view_traveler_profile'))
