#models/traveler_profile.py
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


def get_user_profile(user_id):
    """
    User er unique nomad ID diye tar shob profile data database theke fetch kore.
    """
    return users_collection.find_one({"user_id": user_id})


def update_traveler_profile_info(user_id, data, new_profile_pic_path=None):
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

    # MongoDB te '$set' operator use kore shudhu nirdishto field gulo update kora hocche.
    # Ete onno data change hoy na.
    users_collection.update_one(
        {'user_id': user_id},
        {'$set': update_data}
    )

    # Change confirm korar jonno updated profile ta abar fetch kore return kora hocche.
    return get_user_profile(user_id)

def get_emergency_contacts(user_id):
    """
    Ekjon user er shob emergency contact er list fetch kore.
    """
    user = users_collection.find_one({"user_id": user_id})
    # Jodi user thake ebong tar emergency_contacts field thake, sheta return korbe, noile empty list.
    return user.get('emergency_contacts', []) if user else []

def update_emergency_contacts(user_id, contacts):
    """
    Ekjon user er emergency contact list update kore.
    """
    users_collection.update_one(
        {'user_id': user_id},
        # Puro list take notun list diye replace kora hocche.
        {'$set': {'emergency_contacts': contacts}}
    )

def add_booking_history(user_id, booking):
    """
    User er booking history te notun ekta booking add kore.
    """
    if not user_id or not booking:
        return False
    try:
        # $push operator diye 'bookings' array te notun booking add kora hoy.
        res = users_collection.update_one(
            {'user_id': user_id},
            {'$push': {'bookings': booking}},
            upsert=True # Jodi user er kono booking history age theke na thake, tobe notun toiri korbe.
        )
        return res.modified_count > 0 or res.upserted_id is not None
    except Exception:
        return False

def get_booking_history(user_id):
    """
    Ekjon user er shob booking er list return kore.
    """
    if not user_id:
        return []
    # Shudhu 'bookings' field ta fetch kora hocche performance baranor jonno.
    doc = users_collection.find_one({'user_id': user_id}, {'bookings': 1, '_id': 0})
    return doc.get('bookings', []) if doc else []

def cancel_booking_history(booking_id, user_id):
    """
    User er booking history theke nirdishto booking_id diye ekta booking remove kore.
    """
    if not booking_id or not user_id:
        return False
    try:
        # $pull operator diye 'bookings' array theke nirdishto element remove kora hoy.
        res = users_collection.update_one(
            {'user_id': user_id},
            {'$pull': {'bookings': {'booking_id': booking_id}}}
        )
        # Jodi ekta element o remove hoy, tahole modified_count > 0 hobe.
        return res.modified_count > 0
    except Exception:
        return False
