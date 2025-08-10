
# app.py

from flask import Flask
from dotenv import load_dotenv
import os
from routes.auth import auth_bp
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a-fallback-secret-key')
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5001)