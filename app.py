import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, url_for

#.env file theke environment variables load korte hobe age
load_dotenv()

def create_app():
    #Flask app create and config kora
    app = Flask(__name__)

    #Session er jonno secret key set kora
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    #Routes/Blueprints register kora
    with app.app_context():
        from routes.auth import auth_bp   #Login/Signup related routes
        app.register_blueprint(auth_bp)

        from routes.traveler_profiles import traveler_profiles_bp  #Traveler profile routes
        app.register_blueprint(traveler_profiles_bp)
        
        # Onno teammates ra ekhane tader blueprint register korbe

    #Home page route
    @app.route('/')
    def index():
        if 'user_id' in session:  #Jodi already login kora thake
            return redirect(url_for('auth.dashboard'))  #Dashboard e pathano
        return redirect(url_for('auth.login'))  #Login page e pathano

    return app

#Main file run hole app start hobe
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)  #Debug mode on rakha
