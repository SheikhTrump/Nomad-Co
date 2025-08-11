from pymongo import MongoClient
import os

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client["nomadstay"]
spaces_collection = db["spaces"]

def create_space(space_data):
    """Insert a new space document into MongoDB"""
    return spaces_collection.insert_one(space_data)

def get_all_spaces():
    """Retrieve all spaces"""
    return list(spaces_collection.find({}, {"_id": 0}))
