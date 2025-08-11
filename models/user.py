# models/user.py

from pymongo import MongoClient, ReturnDocument
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId
import os
from datetime import datetime

# MongoDB Connection
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
client = MongoClient(mongo_uri)
db = client.get_database('nomadnest')

users_collection = db.users
counters_collection = db.counters

def calculate_age(dob_string):
    """Calculates age from a date of birth string."""
    if not dob_string:
        return None
    birth_date = datetime.strptime(dob_string, '%Y-%m-%d').date()
    today = datetime.today().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def get_next_nomad_id():
    """Generates a new, unique nomad ID (e.g., nomad#1, nomad#2)."""
    counter = counters_collection.find_one_and_update(
        {'_id': 'user_id_counter'},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return f"nomad#{counter['sequence_value']}"

def create_user(data):
    """Creates a new user (Traveler or Host) and saves it to the database."""
    hashed_password = generate_password_hash(data['password'])
    nomad_id = get_next_nomad_id()
    age = calculate_age(data['dob'])
    
    user_document = {
        "user_id": nomad_id,
        "first_name": data['first_name'],
        "last_name": data['last_name'],
        "dob": data['dob'],
        "age": age,
        "nid": data['nid'],
        "email": data['email'],
        "phone": data['phone'],
        "password": hashed_password,
        "role": data['role']  
    }
    users_collection.insert_one(user_document)
    return nomad_id

def find_user_by_login(login_identifier):
    """Finds a user by their email or user_id from the database."""
    user = users_collection.find_one({"email": login_identifier})
    if not user:
        user = users_collection.find_one({"user_id": login_identifier})
    return user