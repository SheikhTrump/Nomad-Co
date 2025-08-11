#models/space.py

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId #ObjectId import kora dorkar

try:
    #.env file theke MONGO_URI ta load korbe
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/nomadnest')
    client = MongoClient(mongo_uri)
    db = client.get_database('nomadnest')
    spaces_collection = db.spaces
    print("Space Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Space Model: Error connecting to MongoDB: {e}")

def get_all_spaces():
    #Database theke shob space er list fetch kore
    return list(spaces_collection.find())

def get_space_by_id(space_id):
    #Ekta single space er details ID diye fetch kore
    return spaces_collection.find_one({"_id": ObjectId(space_id)})

def filter_spaces(filters):
    #Eita ekta empty dictionary jekhane amra filter condition gulo joma korbo
    query = {}
    
    #Price Range Filter er logic
    price_query = {}
    try:
        if filters.get('min_price'):
            price_query['$gte'] = int(filters['min_price']) #gte mane "greater than or equal"
        if filters.get('max_price'):
            price_query['$lte'] = int(filters['max_price']) #lte mane "less than or equal"
        if price_query:
            query['price_per_month'] = price_query
    except ValueError:
        pass

    #Location diye filter korar logic
    if filters.get('location'):
        query['location_city'] = {'$regex': filters['location'], '$options': 'i'} #'i' mane case-insensitive

    #Coworking space ache kina sheta check korar logic
    if filters.get('coworking'):
        query['has_coworking_space'] = True
        
    #Space er type (Private/Shared) diye filter korar logic
    if filters.get('space_type'):
        query['space_type'] = filters['space_type']
        
    #Amenities (WiFi, AC, etc.) diye filter korar logic
    if filters.get('amenities'):
        query['amenities'] = {'$all': filters.get('amenities')} #'$all' mane shobgulo amenity thakte hobe

    #Sort korar logic
    sort_order = []
    if filters.get('sort_by') == 'price_asc':
        sort_order.append(('price_per_month', ASCENDING)) #Kom theke beshi
    elif filters.get('sort_by') == 'price_desc':
        sort_order.append(('price_per_month', DESCENDING)) #Beshi theke kom
    
    #Filter ebong sort apply kore final result return korbe
    if sort_order:
        return list(spaces_collection.find(query).sort(sort_order))
    else:
        return list(spaces_collection.find(query))

def add_sample_spaces():
    #Jodi database e kono space na thake, tahole testing er jonno 15 ta sample data add kore
    if spaces_collection.count_documents({}) == 0:
        print("No spaces found. Adding 20 sample spaces...")
        #(Ekhane 15 ta sample space er list thakbe)
        sample_data = [
            #Dhaka Division
            {"name": "Urban Oasis Loft", "location_city": "Dhaka", "price_per_month": 35000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["Gym", "Rooftop Access", "High-Speed WiFi"], "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?q=80&w=2070&auto=format&fit=crop"},
            {"name": "The Gulshan Getaway", "location_city": "Dhaka", "price_per_month": 55000, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["Pool", "Gym", "Parking"], "image_url": "https://images.unsplash.com/photo-1594563703937-fdc640497dcd?q=80&w=1974&auto=format&fit=crop"},
            {"name": "Dhanmondi Creative Hub", "location_city": "Dhaka", "price_per_month": 30000, "has_coworking_space": True, "space_type": "Shared Room", "amenities": ["Kitchen", "High-Speed WiFi"], "image_url": "https://images.unsplash.com/photo-1499750310107-5fef28a66643?q=80&w=2070&auto=format&fit=crop"},

            #Chittagong Division
            {"name": "Port City Connect", "location_city": "Chittagong", "price_per_month": 32000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["Rooftop Access", "High-Speed WiFi"], "image_url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?q=80&w=2070&auto=format&fit=crop"},
            {"name": "Comilla Collab House", "location_city": "Comilla", "price_per_month": 16000, "has_coworking_space": True, "space_type": "Shared Room", "amenities": ["High-Speed WiFi"], "image_url": "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?q=80&w=2232&auto=format&fit=crop"},

            #Sylhet Division
            {"name": "Mountain Retreat", "location_city": "Sylhet", "price_per_month": 22000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["Rooftop Access", "Kitchen"], "image_url": "https://images.unsplash.com/photo-1505691938895-1758d7feb511?q=80&w=1974&auto=format&fit=crop"},

            #Khulna Division
            {"name": "Sundarbans Gateway", "location_city": "Khulna", "price_per_month": 20000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi"], "image_url": "https://images.unsplash.com/photo-1582268611958-ebfd161ef9cf?q=80&w=2070&auto=format&fit=crop"},
            {"name": "Jessore Junction", "location_city": "Jessore", "price_per_month": 15000, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["Kitchen"], "image_url": "https://images.unsplash.com/photo-1484154218962-a197022b5858?q=80&w=2074&auto=format&fit=crop"},

            #Rajshahi Division
            {"name": "The Minimalist Studio", "location_city": "Rajshahi", "price_per_month": 17000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["AC", "High-Speed WiFi"], "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?q=80&w=1980&auto=format&fit=crop"},

            #Barisal Division
            {"name": "Riverside Work Pods", "location_city": "Barisal", "price_per_month": 18000, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["AC"], "image_url": "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?q=80&w=2072&auto=format&fit=crop"},
            {"name": "Patuakhali Peace Place", "location_city": "Patuakhali", "price_per_month": 13000, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["Kitchen"], "image_url": "https://images.unsplash.com/photo-1523217582562-09d0def993a6?q=80&w=1780&auto=format&fit=crop"},

            #Rangpur Division
            {"name": "Rangpur Residence", "location_city": "Rangpur", "price_per_month": 12000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi"], "image_url": "https://images.unsplash.com/photo-1570129477492-45c003edd2be?q=80&w=2070&auto=format&fit=crop"},
            {"name": "Dinajpur Dwelling", "location_city": "Dinajpur", "price_per_month": 11000, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["Kitchen"], "image_url": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?q=80&w=1974&auto=format&fit=crop"},

            #Mymensingh Division
            {"name": "Mymensingh Manor", "location_city": "Mymensingh", "price_per_month": 14000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["AC"], "image_url": "https://images.unsplash.com/photo-1568605114967-8130f3a36994?q=80&w=2070&auto=format&fit=crop"},
            {"name": "Netrokona Nook", "location_city": "Netrokona", "price_per_month": 9000, "has_coworking_space": False, "space_type": "Shared Room", "amenities": [], "image_url": "https://images.unsplash.com/photo-1513584684374-8bab748fbf90?q=80&w=2065&auto=format&fit=crop"}
        ]
        spaces_collection.insert_many(sample_data)
        print(f"{len(sample_data)} sample spaces added.")
