import os
from pymongo import MongoClient

#MongoDB connection setup kortesi
try:
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')  #MongoDB URI set korlam
    client = MongoClient(mongo_uri)  #Client create hocche
    db = client.get_database('nomadnest')  #Database select hobe er maddhome
    users_collection = db.users  #Users collection select er jonne
    print("Traveler Profile Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Traveler Profile Model: Error connecting to MongoDB: {e}")

#User er pura profile fetch korar function
def get_user_profile(user_id):
    return users_collection.find_one({"user_id": user_id})

#User profile update korar function
def update_traveler_profile_info(user_id, data, new_profile_pic_path=None):
    #Update er jonno specific fields ready kora
    update_data = {
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name'),
        'email': data.get('email'),
        'bio': data.get('bio'),
        'max_budget': int(data.get('max_budget', 1000)),  #Default 1000
        'min_wifi_speed': int(data.get('min_wifi_speed', 25)),  #Default 25
    }

    #Jodi new profile picture path thake tahole add kora
    if new_profile_pic_path:
        update_data['profile_picture_url'] = new_profile_pic_path

    #MongoDB te $set diye only given fields update kora
    users_collection.update_one(
        {'user_id': user_id},
        {'$set': update_data}
    )

    #Update confirm korar jonno updated profile return kora
    return get_user_profile(user_id)
