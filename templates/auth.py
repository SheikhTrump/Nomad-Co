# routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

from models.user import create_traveler, find_user_by_login


auth_bp = Blueprint('auth', __name__, template_folder='templates')


DEFAULT_ADMIN_USER = {'email': 'admin@nomad.com', 'password': 'adminpassword'}
DEFAULT_HOST_USER = {'email': 'host@nomad.com', 'password': 'hostpassword'}


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
            'confirm_password': request.form.get('confirm_password')
        }

        if form_data['password'] != form_data['confirm_password']:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.signup'))

        try:
            new_user_id = create_traveler(form_data)
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

        
        if login_identifier == DEFAULT_ADMIN_USER['email'] and password == DEFAULT_ADMIN_USER['password']:
            session['role'] = 'admin'
            session['user_id'] = 'ADMIN'
            flash('Admin login successful', 'success')
            return redirect(url_for('auth.dashboard'))

       
        if login_identifier == DEFAULT_HOST_USER['email'] and password == DEFAULT_HOST_USER['password']:
            session['role'] = 'host'
            session['user_id'] = 'HOST'
            flash('Host login successful', 'success')
            return redirect(url_for('auth.dashboard'))

        
        user = find_user_by_login(login_identifier)
        if user and check_password_hash(user['password'], password):
            session['role'] = 'traveler'
            session['user_id'] = user['user_id']
            session['first_name'] = user['first_name']
            flash(f"Welcome {user['first_name']}", 'success')
            return redirect(url_for('auth.dashboard'))

    
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
