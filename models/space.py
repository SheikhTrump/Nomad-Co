

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId
from datetime import datetime

try:
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
    client = MongoClient(mongo_uri)
    db = client.get_database('nomadnest')
    spaces_collection = db.spaces
    print("Space Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Space Model: Error connecting to MongoDB: {e}")



def create_space(space_data):
    
    space_data['created_at'] = datetime.utcnow()
    return spaces_collection.insert_one(space_data)


def get_all_spaces():
    return list(spaces_collection.find())


def get_space_by_id(space_id):
    return spaces_collection.find_one({"_id": ObjectId(space_id)})


def filter_spaces(filters):
    query = {}
    price_query = {}

    # Price filtering
    try:
        if filters.get('min_price'):
            price_query['$gte'] = float(filters['min_price'])
        if filters.get('max_price'):
            price_query['$lte'] = float(filters['max_price'])
        if price_query:
            query['price_per_night'] = price_query
    except ValueError:
        pass

    # Location
    if filters.get('location'):
        query['location_city'] = {'$regex': filters['location'], '$options': 'i'}

    # Coworking
    if filters.get('coworking'):
        query['has_coworking_space'] = True

    # Space type
    if filters.get('space_type'):
        query['space_type'] = filters['space_type']

    # Amenities
    if filters.get('amenities'):
        query['amenities'] = {'$all': filters.get('amenities')}

    # Sorting
    sort_order = []
    if filters.get('sort_by') == 'price_asc':
        sort_order.append(('price_per_night', ASCENDING))
    elif filters.get('sort_by') == 'price_desc':
        sort_order.append(('price_per_night', DESCENDING))

    if sort_order:
        return list(spaces_collection.find(query).sort(sort_order))
    else:
        return list(spaces_collection.find(query))


def update_space(space_id, updated_data):
   
    return spaces_collection.update_one(
        {"_id": ObjectId(space_id)},
        {"$set": updated_data}
    )


def delete_space(space_id):
  
    return spaces_collection.delete_one({"_id": ObjectId(space_id)})



def add_sample_spaces():
    if spaces_collection.count_documents({}) == 0:
        print("No spaces found. Adding sample spaces...")
        sample_data = [
            {
                "host_id": "samplehost1",
                "host_name": "John Doe",
                "host_email": "john@example.com",
                "host_phone": "+880123456789",
                "space_title": "Urban Oasis Loft",
                "description": "A cozy loft in the heart of Dhaka.",
                "location_city": "Dhaka",
                "location": {"latitude": 23.8103, "longitude": 90.4125},
                "price_per_night": 3500,
                "has_coworking_space": True,
                "space_type": "Private Room",
                "amenities": ["Gym", "Rooftop Access", "High-Speed WiFi"],
                "photos": ["https://images.unsplash.com/photo-1522708323590-d24dbb6b0267"],
                "created_at": datetime.utcnow()
            },
            {
                "host_id": "samplehost2",
                "host_name": "Jane Smith",
                "host_email": "jane@example.com",
                "host_phone": "+880987654321",
                "space_title": "The Gulshan Getaway",
                "description": "Luxury apartment with pool and gym.",
                "location_city": "Dhaka",
                "location": {"latitude": 23.7806, "longitude": 90.4223},
                "price_per_night": 5500,
                "has_coworking_space": True,
                "space_type": "Full Apartment",
                "amenities": ["Pool", "Gym", "Parking"],
                "photos": ["https://images.unsplash.com/photo-1594563703937-fdc640497dcd"],
                "created_at": datetime.utcnow()
            }
        ]
        spaces_collection.insert_many(sample_data)
        print(f"{len(sample_data)} sample spaces added.")


