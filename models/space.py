

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from datetime import datetime
import os

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
    """
    Accepts either a hex string id or an ObjectId and returns the space document (or None).
    """
    try:
        _id = ObjectId(space_id) if not isinstance(space_id, ObjectId) else space_id
    except Exception:
        # If conversion fails, try using the raw value (some records may store string ids)
        _id = space_id
    return spaces_collection.find_one({'_id': _id})


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

def add_booking_to_space(space_id, booking):
    """
    Push a booking dict into the space's 'bookings' array.
    Returns True if the space was matched and updated.
    """
    try:
        _id = ObjectId(space_id) if not isinstance(space_id, ObjectId) else space_id
    except Exception:
        _id = space_id
    res = spaces_collection.update_one({'_id': _id}, {'$push': {'bookings': booking}})
    return res.modified_count > 0

def cancel_booking_in_space(booking_id, user_id):
    """
    Remove a booking from any space's bookings array where booking_id and user_id match.
    Returns True if a booking was removed.
    """
    if not booking_id:
        return False
    # Try to remove by matching booking_id and user_id
    try:
        res = spaces_collection.update_one(
            {'bookings.booking_id': booking_id, 'bookings.user_id': user_id},
            {'$pull': {'bookings': {'booking_id': booking_id, 'user_id': user_id}}}
        )
        return res.modified_count > 0
    except Exception:
        return False


