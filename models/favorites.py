# models/favorites.py

from bson.objectid import ObjectId
# We will use the 'db' and 'users_collection' from your existing user model
# to ensure we are all using the same database connection.
from models.user import db, users_collection

# We also need a reference to the spaces collection to fetch favorite details
spaces_collection = db.spaces

def add_favorite_to_user(user_id, space_id):
    """Adds a space's ID to a user's 'favorites' list in the users collection."""
    users_collection.update_one(
        {"user_id": user_id},
        # '$addToSet' ensures a space is not added more than once
        {"$addToSet": {"favorites": ObjectId(space_id)}}
    )

def remove_favorite_from_user(user_id, space_id):
    """Removes a space's ID from a user's 'favorites' list."""
    users_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"favorites": ObjectId(space_id)}}
    )

def get_user_favorite_ids(user_id):
    """Gets a list of just the IDs of a user's favorite spaces."""
    user = users_collection.find_one({"user_id": user_id}, {"favorites": 1, "_id": 0})
    if user and 'favorites' in user:
        # Convert ObjectId to string for easier comparison in the template
        return [str(space_id) for space_id in user['favorites']]
    return []

def get_user_favorite_spaces(user_id):
    """Gets the full document details for all of a user's favorite spaces."""
    user = users_collection.find_one({"user_id": user_id})
    if not user or 'favorites' not in user:
        return []
    
    favorite_space_ids = user['favorites']
    # Find all spaces whose _id is in the user's favorites list
    return list(spaces_collection.find({"_id": {"$in": favorite_space_ids}}))
