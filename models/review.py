#models/review.py

import os
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

try:
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
    client = MongoClient(mongo_uri)
    db = client.get_database('nomadnest')
    reviews_collection = db.reviews
    spaces_collection = db.spaces # Space collection reference
    print("Review Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Review Model: Error connecting to MongoDB: {e}")


def create_review(space_id, user_id, user_name, rating, comment, photo_url=None):
    """Database e ekta notun review save kore."""
    review_document = {
        "space_id": ObjectId(space_id),
        "user_id": user_id,
        "user_name": user_name,
        "rating": int(rating),
        "comment": comment,
        "photo_url": photo_url,
        "created_at": datetime.utcnow()
    }
    return reviews_collection.insert_one(review_document)

def get_reviews_for_space(space_id):
    """Ekta specific space er shob review fetch kore."""
    return list(reviews_collection.find({"space_id": ObjectId(space_id)}).sort("created_at", -1))

# --- NEW: Function to get all reviews by a specific user ---
def get_reviews_by_user(user_id):
    """
    Ekjon specific user er deya shob review fetch kore.
    """
    user_reviews = list(reviews_collection.find({"user_id": user_id}).sort("created_at", -1))
    # For each review, fetch the details of the space it belongs to
    for review in user_reviews:
        space_details = spaces_collection.find_one({"_id": review['space_id']})
        review['space_details'] = space_details
    return user_reviews

def get_average_rating_for_space(space_id):
    """Ekta space er average rating calculate kore."""
    reviews = get_reviews_for_space(space_id)
    if not reviews:
        return 0, 0
    
    total_rating = sum(r['rating'] for r in reviews)
    average_rating = round(total_rating / len(reviews), 1)
    return average_rating, len(reviews)
