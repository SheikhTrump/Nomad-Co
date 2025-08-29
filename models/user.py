from pymongo import MongoClient, ReturnDocument
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId, InvalidId
import os
from datetime import datetime
from flask import session

mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
client = MongoClient(mongo_uri)
db = client.get_database('nomadnest')

users_collection = db.users
counters_collection = db.counters


def calculate_age(dob_string):
    if not dob_string:
        return None
    birth_date = datetime.strptime(dob_string, '%Y-%m-%d').date()
    today = datetime.today().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age


def get_next_nomad_id():
    counter = counters_collection.find_one_and_update(
        {'_id': 'user_id_counter'},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return f"nomad#{counter['sequence_value']}"


def create_user(data):
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
        "role": data['role'],
        "verification": {
            "status": "not_submitted",
            "nid_photo": "",
            "own_photo": ""
        }
    }
    result = users_collection.insert_one(user_document)
    
    return str(result.inserted_id)


def find_user_by_login(login_identifier):
    user = users_collection.find_one({"email": login_identifier})
    if not user:
        user = users_collection.find_one({"user_id": login_identifier})
    return user


def submit_verification_photos(user_id, nid_photo, own_photo):
    
    upload_folder = "static/uploads"
    os.makedirs(upload_folder, exist_ok=True)
    nid_filename = f"nid_{user_id}.jpg"
    own_filename = f"own_{user_id}.jpg"
    nid_path = f"{upload_folder}/{nid_filename}"
    own_path = f"{upload_folder}/{own_filename}"
    nid_photo.save(nid_path)
    own_photo.save(own_path)
    
    if is_valid_objectid(user_id):
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "verification": {
                    "nid_photo": nid_path,
                    "own_photo": own_path,
                    "status": "pending"
                }
            }}
        )
    else:
        db.users.update_one(
            {"_id": user_id},
            {"$set": {
                "verification": {
                    "nid_photo": nid_path,
                    "own_photo": own_path,
                    "status": "pending"
                }
            }}
        )


def is_valid_objectid(oid):
    try:
        ObjectId(oid)
        return True
    except (InvalidId, TypeError):
        return False


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    if is_valid_objectid(user_id):
        return db.users.find_one({"_id": ObjectId(user_id)})
    else:
        return db.users.find_one({"_id": user_id})
