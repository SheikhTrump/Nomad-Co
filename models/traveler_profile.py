# models/traveler_profile.py
# Ei file ta traveler er profile, emergency contact, ebong booking history manage kore.

import os
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

# Database Connection
try:
    # Environment variable theke MONGO_URI neyar cheshta hocche
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
    client = MongoClient(mongo_uri)
    db = client.get_database('nomadnest')
    # Amra ekhane 'users' collection er jonno ekta reference toiri korchi.
    users_collection = db.users
    print("Traveler Profile Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Traveler Profile Model: Error connecting to MongoDB: {e}")


def get_user_profile(user_obj_id):
    """
    User er unique MongoDB _id diye tar shob profile data database theke fetch kore.
    """
    # CORRECTED: Query by '_id' and convert the string from the session to an ObjectId
    return users_collection.find_one({"_id": ObjectId(user_obj_id)})


def update_traveler_profile_info(user_obj_id, data, new_profile_pic_path=None):
    """
    Traveler profile page theke je field gulo update kora hoy, shegulo database e save kore.
    """
    # Je je field update kora hobe, shegular jonno ekta dictionary toiri kora hocche.
    update_data = {
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'bio': data.get('bio'),
        'max_budget': int(data.get('max_budget', 1000)),
        'min_wifi_speed': int(data.get('min_wifi_speed', 25)),
        'looking_for': data.get('looking_for', '')
    }

    # Jodi notun profile picture upload kora hoy, tahole shetar path add kora hobe.
    if new_profile_pic_path:
        update_data['profile_picture_url'] = new_profile_pic_path

    # CORRECTED: Query by '_id' to update the correct user document.
    users_collection.update_one(
        {'_id': ObjectId(user_obj_id)},
        {'$set': update_data}
    )

    # Change confirm korar jonno updated profile ta abar fetch kore return kora hocche.
    return get_user_profile(user_obj_id)

def get_emergency_contacts(user_obj_id):
    """
    Ekjon user er shob emergency contact er list fetch kore.
    """
    # CORRECTED: Query by '_id'
    user = users_collection.find_one({"_id": ObjectId(user_obj_id)})
    # Jodi user thake ebong tar emergency_contacts field thake, sheta return korbe, noile empty list.
    return user.get('emergency_contacts', []) if user else []

def update_emergency_contacts(user_obj_id, contacts):
    """
    Ekjon user er emergency contact list update kore.
    """
    # CORRECTED: Query by '_id'
    users_collection.update_one(
        {'_id': ObjectId(user_obj_id)},
        # Puro list take notun list diye replace kora hocche.
        {'$set': {'emergency_contacts': contacts}}
    )

def add_booking_history(user_obj_id, booking):
    """
    User er booking history te notun ekta booking add kore.
    """
    if not user_obj_id or not booking:
        return False
    try:
        # CORRECTED: Query by '_id'
        res = users_collection.update_one(
            {'_id': ObjectId(user_obj_id)},
            {'$push': {'bookings': booking}},
            upsert=True # Jodi user er kono booking history age theke na thake, tobe notun toiri korbe.
        )
        return res.modified_count > 0 or res.upserted_id is not None
    except Exception:
        return False

def get_booking_history(user_obj_id):
    """
    Ekjon user er shob booking er list return kore.
    """
    if not user_obj_id:
        return []
    # CORRECTED: Query by '_id'
    doc = users_collection.find_one({'_id': ObjectId(user_obj_id)}, {'bookings': 1, '_id': 0})
    return doc.get('bookings', []) if doc else []

def cancel_booking_history(booking_id, user_obj_id):
    """
    User er booking history theke nirdishto booking_id diye ekta booking remove kore.
    """
    if not booking_id or not user_obj_id:
        return False
    try:
        # CORRECTED: Query by '_id'
        res = users_collection.update_one(
            {'_id': ObjectId(user_obj_id)},
            {'$pull': {'bookings': {'booking_id': booking_id}}}
        )
        # Jodi ekta element o remove hoy, tahole modified_count > 0 hobe.
        return res.modified_count > 0
    except Exception:
        return False
