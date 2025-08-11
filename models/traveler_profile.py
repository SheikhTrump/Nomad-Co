#models/traveler_profile.py

import os
from pymongo import MongoClient

#Database Connection
try:
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
    client = MongoClient(mongo_uri)
    db = client.get_database('nomadnest')
    #Amra ekhane users collection er jonno nijeder reference toiri korchi.
    users_collection = db.users
    print("Traveler Profile Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Traveler Profile Model: Error connecting to MongoDB: {e}")


def get_user_profile(user_id):
    """
    User er unique nomad ID diye tar shob profile data fetch kore.
    Ei function ta ekhon ei file er moddhei ache.
    """
    return users_collection.find_one({"user_id": user_id})


def update_traveler_profile_info(user_id, data, new_profile_pic_path=None):
    """
    Traveler profile page theke je field gulo update kora hoy, shegulo handle kore.
    """
    update_data = {
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'bio': data.get('bio'),
        'max_budget': int(data.get('max_budget', 1000)),
        'min_wifi_speed': int(data.get('min_wifi_speed', 25)),
        #FIXED: 'looking_for' field ta ekhane add kora hoyeche jate update hoy
        'looking_for': data.get('looking_for', '')
    }

    #Shudhu notun profile picture upload dilei URL ta update hobe
    if new_profile_pic_path:
        update_data['profile_picture_url'] = new_profile_pic_path

    #MongoDB te '$set' operator use kore shudhu nirdishto field gulo update kora hocche
    users_collection.update_one(
        {'user_id': user_id},
        {'$set': update_data}
    )

    #Change confirm korar jonno updated profile ta return kora hocche.
    return get_user_profile(user_id)
