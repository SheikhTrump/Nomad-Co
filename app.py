# app.py

import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, url_for

from routes.auth import auth_bp
from routes.traveler_profiles import traveler_profiles_bp
from routes.space_filters import space_filters_bp
from routes.reviews import reviews_bp
from routes.api import api_bp
from routes.space import space_bp

load_dotenv()

def create_app():

    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a-default-secret-key')

    with app.app_context():
        app.register_blueprint(auth_bp)
        app.register_blueprint(traveler_profiles_bp)
        app.register_blueprint(space_filters_bp)
        app.register_blueprint(reviews_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(space_bp)

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('auth.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
