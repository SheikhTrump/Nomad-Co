# routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import check_password_hash
from models.user import create_user, find_user_by_login, update_last_login, db
from models.traveler_profile import get_user_profile
from bson.objectid import ObjectId

auth_bp = Blueprint('auth', __name__, template_folder='templates')


# Default Admin credentials
DEFAULT_ADMIN_USER = {'email': 'admin@nomad.com', 'password': 'Black'}


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        form_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'dob': request.form.get('dob'),
            'nid': request.form.get('nid'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'password': request.form.get('password'),
            'confirm_password': request.form.get('confirm_password'),
            'role': request.form.get('role')
        }

        if form_data['password'] != form_data['confirm_password']:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.signup'))

        if find_user_by_login(form_data['email']):
            flash('This email address is already registered.', 'danger')
            return redirect(url_for('auth.signup'))

        try:
            new_user_id = create_user(form_data)
            # CORRECTED: Do not log the user in automatically after signup.
            # Instead, flash a success message and redirect them to the login page.
            flash(f'Account created successfully! Your User ID is {new_user_id}. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('auth.signup'))

    response = make_response(render_template('signup.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        login_identifier = request.form.get('login_identifier')
        password = request.form.get('password')

        if login_identifier == DEFAULT_ADMIN_USER['email'] and password == DEFAULT_ADMIN_USER['password']:
            session['role'] = 'admin'
            session['user_id'] = 'ADMIN'
            session['first_name'] = 'Admin'
            flash('Admin login successful', 'success')
            return redirect(url_for('auth.dashboard'))

        user = find_user_by_login(login_identifier)
        if user and check_password_hash(user['password'], password):
            session['role'] = user['role']
            session['user_id'] = str(user['_id']) # Keep this for database queries
            session['nomad_id'] = user['user_id'] # Add this for display purposes
            session['first_name'] = user['first_name']
            
            # Update last_login timestamp on successful login
            update_last_login(user['user_id'])
            
            if user['role'] == 'host':
                flash('Host login successful', 'success')
            else:
                flash(f"Welcome {user['first_name']}", 'success')

            return redirect(url_for('auth.dashboard'))

        flash('Invalid credentials. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@auth_bp.route('/dashboard')
def dashboard():
    dashboard_data = {}
    if 'user_id' not in session:
        flash('You need to be logged in to view the dashboard.', 'warning')
        return redirect(url_for('auth.login'))
        
    if session.get('role') == 'admin':
        dashboard_data['pending_hosts'] = list(db.users.find({
            "role": "host",
            "verification.status": "pending"
        }))
        # You can add more admin-specific data here
    else:
        try:
            user = db.users.find_one({'_id': ObjectId(session['user_id'])})
            dashboard_data['user'] = user
        except Exception:
            user = None
            # If ObjectId fails, it might be the custom ID, handle accordingly or log out
            session.clear()
            flash('There was an error with your session. Please log in again.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('dashboard.html', **dashboard_data)


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


