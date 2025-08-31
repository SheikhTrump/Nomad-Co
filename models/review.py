#models/review.py
# Ei file ta user review shomporkito shob database kaaj handle kore.

import os
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

try:
    # MongoDB connection string environment variable theke neyar cheshta kora hocche.
    # Jodi na paowa jay, tahole default local address use kora hobe.
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
    client = MongoClient(mongo_uri)
    db = client.get_database('nomadnest')
    # 'reviews' and 'spaces' collection er reference toiri kora hocche.
    reviews_collection = db.reviews
    spaces_collection = db.spaces # Space collection er reference
    print("Review Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Review Model: Error connecting to MongoDB: {e}")


def create_review(space_id, user_id, user_name, rating, comment, photo_url=None):
    """Database e ekta notun review toiri kore ebong save kore."""
    # Review er jonno ekta document (dictionary) toiri kora hocche.
    review_document = {
        "space_id": ObjectId(space_id), # space_id ke ObjectId te convert kora hocche
        "user_id": user_id,
        "user_name": user_name,
        "rating": int(rating), # rating string theke integer e convert kora hocche
        "comment": comment,
        "photo_url": photo_url,
        "created_at": datetime.utcnow() # review toirir shomoy save kora hocche
    }
    # reviews_collection e document ta insert kora hocche.
    return reviews_collection.insert_one(review_document)

def get_reviews_for_space(space_id):
    """Ekta nirdishto space er shob review database theke fetch kore."""
    # space_id diye shob matching review khuje ber kora hocche.
    # created_at onujayi notun theke purono (descending) shajano hocche.
    return list(reviews_collection.find({"space_id": ObjectId(space_id)}).sort("created_at", -1))

# --- NEW: Ekjon nirdishto user er shob review paowar jonno function ---
def get_reviews_by_user(user_id):
    """
    Ekjon nirdishto user er deya shob review database theke fetch kore.
    """
    # user_id diye shob matching review khuje ber kora hocche.
    user_reviews = list(reviews_collection.find({"user_id": user_id}).sort("created_at", -1))
    
    # Prottekta review er jonno, oi review ta kon space er, shetar details fetch kora hocche.
    for review in user_reviews:
        space_details = spaces_collection.find_one({"_id": review['space_id']})
        # review document er moddhe space er details add kora hocche.
        review['space_details'] = space_details
    return user_reviews

def get_average_rating_for_space(space_id):
    """Ekta nirdishto space er shob review er rating er average hishab kore."""
    # space er shob review fetch kora hocche.
    reviews = get_reviews_for_space(space_id)
    # Jodi kono review na thake, tahole 0 return kora hocche.
    if not reviews:
        return 0, 0
    
    # Shob rating jog kora hocche.
    total_rating = sum(r['rating'] for r in reviews)
    # Average hishab kora hocche and ek doshomik sthan porjonto rakha hocche.
    average_rating = round(total_rating / len(reviews), 1)
    # Gor rating ebong total review shongkhya return kora hocche.
    return average_rating, len(reviews)
