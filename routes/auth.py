# routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
# We now import the generic create_user function
from models.user import create_user, find_user_by_login

auth_bp = Blueprint('auth', __name__, template_folder='templates')

# Default Admin credentials (remains unchanged)
DEFAULT_ADMIN_USER = {'email': 'admin@nomad.com', 'password': 'adminpassword'}
# DEFAULT_HOST_USER is now removed

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
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
            'role': request.form.get('role')  # Get the selected role
        }

        if form_data['password'] != form_data['confirm_password']:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.signup'))

        # Check if email already exists
        if find_user_by_login(form_data['email']):
            flash('This email address is already registered.', 'danger')
            return redirect(url_for('auth.signup'))

        try:
            # Call the generic create_user function
            new_user_id = create_user(form_data)
            flash(f'Account created successfully! Your User ID is {new_user_id}', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('auth.signup'))

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_identifier = request.form.get('login_identifier')
        password = request.form.get('password')

        # Admin login check (unchanged)
        if login_identifier == DEFAULT_ADMIN_USER['email'] and password == DEFAULT_ADMIN_USER['password']:
            session['role'] = 'admin'
            session['user_id'] = 'ADMIN'
            session['first_name'] = 'Admin' # Add a name for the dashboard
            flash('Admin login successful', 'success')
            return redirect(url_for('auth.dashboard'))

        # Host and Traveler login check (now both from database)
        user = find_user_by_login(login_identifier)
        if user and check_password_hash(user['password'], password):
            session['role'] = user['role']
            session['user_id'] = user['user_id']
            session['first_name'] = user['first_name']
            
            if user['role'] == 'host':
                flash('Host login successful', 'success')
            else: # Traveler
                flash(f"Welcome {user['first_name']}", 'success')

            return redirect(url_for('auth.dashboard'))

        # If no match is found
        flash('Invalid credentials. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))