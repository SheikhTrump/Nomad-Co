#models\space.py

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId
from datetime import datetime

# --- MongoDB Connect ---
try:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/nomadnest")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client.get_database("nomadnest")
    spaces_collection = db.spaces
    # Helpful indexes for filtering
    spaces_collection.create_index([("price_per_night", ASCENDING)])
    spaces_collection.create_index([("location_city", ASCENDING)])
    spaces_collection.create_index([("has_coworking_space", ASCENDING)])
    print("Space Model: MongoDB connected successfully.")
except Exception as e:
    print(f"Space Model: Error connecting to MongoDB: {e}")

# --- CRUD helpers ---
def create_space(space_data):
    space_data["created_at"] = datetime.utcnow()
    return spaces_collection.insert_one(space_data)

def get_all_spaces():
    return list(spaces_collection.find())

def get_space_by_id(space_id):
    """
    Accepts either a hex string id or an ObjectId and returns the space document (or None).
    """
    try:
        _id = ObjectId(space_id) if not isinstance(space_id, ObjectId) else space_id
        return spaces_collection.find_one({"_id": _id})
    except Exception:
        return None


def update_space(space_id, updated_data):
    return spaces_collection.update_one(
        {"_id": ObjectId(space_id)},
        {"$set": updated_data}
    )

def delete_space(space_id):
    return spaces_collection.delete_one({"_id": ObjectId(space_id)})


def get_spaces_by_host(host_id):
    """Fetches all spaces created by a specific host."""
    return list(spaces_collection.find({"host_id": host_id}))

def get_popular_spaces_in_location(location_city, exclude_id=None, limit=4):
    """
    Finds other spaces in the same city, excluding the specified ID.
    Converts ObjectId to string to make the result JSON serializable for sessions.
    """
    query = {
        "location_city": location_city,
        "_id": {"$ne": ObjectId(exclude_id)} if exclude_id else {"$exists": True}
    }
    spaces = list(spaces_collection.find(query).limit(limit))
    # Convert ObjectId to string for each document
    for space in spaces:
        space['_id'] = str(space['_id'])
    return spaces


# --- Filter & sort ---
def filter_spaces(filters, user_profile=None):
    query = {}

    if filters.get('host_id'):
        query['host_id'] = filters['host_id']

    price_query = {}
    try:
        if filters.get("min_price") is not None and filters.get("min_price") != '':
            price_query["$gte"] = int(filters.get("min_price"))
        if filters.get("max_price") is not None and filters.get("max_price") != '':
            price_query["$lte"] = int(filters.get("max_price"))
        if price_query:
            query["price_per_night"] = price_query
    except (ValueError, TypeError):
        pass

    if filters.get("location"):
        query["location_city"] = {"$regex": filters["location"], "$options": "i"}

    if filters.get("coworking"):
        query["has_coworking_space"] = True

    if filters.get("space_type"):
        query["space_type"] = filters["space_type"]

    if filters.get("amenities"):
        query["amenities"] = {"$all": filters.get("amenities")}

    matching = list(spaces_collection.find(query))

    if filters.get("sort_by") == "best_match" and user_profile:
        scored = []
        user_budget_monthly = user_profile.get("max_budget", 0) or 0
        user_budget_nightly = user_budget_monthly / 30 if user_budget_monthly else 0
        min_wifi = user_profile.get("min_wifi_speed", 0) or 0
        for sp in matching:
            score = 0.0
            price = sp.get("price_per_night", 0) or 0
            wifi = sp.get("wifi_speed_mbps", 0) or 0
            diff = user_budget_nightly - price
            if diff >= 0:
                score += diff * 0.1
            if wifi >= min_wifi:
                score += (wifi - min_wifi)
            scored.append({"space": sp, "score": score})
        return [x["space"] for x in sorted(scored, key=lambda x: x["score"], reverse=True)]

    sort_order = []
    if filters.get("sort_by") == "price_asc":
        sort_order.append(("price_per_night", ASCENDING))
    elif filters.get("sort_by") == "price_desc":
        sort_order.append(("price_per_night", DESCENDING))

    return list(spaces_collection.find(query).sort(sort_order)) if sort_order else matching

# --- Booking Management ---
def add_booking_to_space(space_id, booking):
    try:
        _id = ObjectId(space_id) if not isinstance(space_id, ObjectId) else space_id
    except Exception:
        _id = space_id
    res = spaces_collection.update_one({'_id': _id}, {'$push': {'bookings': booking}})
    return res.modified_count > 0

def cancel_booking_in_space(booking_id, user_id):
    if not booking_id:
        return False
    try:
        res = spaces_collection.update_one(
            {'bookings.booking_id': booking_id, 'bookings.user_id': user_id},
            {'$pull': {'bookings': {'booking_id': booking_id, 'user_id': user_id}}}
        )
        return res.modified_count > 0
    except Exception:
        return False


# --- Sample data utilities ---

def _picsum(seed: str, w: int = 800, h: int = 600):
    return [
        f"https://picsum.photos/seed/{seed}-1/{w}/{h}",
        f"https://picsum.photos/seed/{seed}-2/{w}/{h}",
        f"https://picsum.photos/seed/{seed}-3/{w}/{h}",
    ]


def add_sample_spaces():
    if spaces_collection.count_documents({}) == 0:
        print("No spaces found. Adding 26 sample spaces...")
        sample_data = [
            # Dhaka (3)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Gulshan Modern Apartment", "description": "A stylish apartment in the heart of Gulshan with all modern amenities.", "location_city": "Dhaka", "latitude": 23.7925, "longitude": 90.4078, "price_per_night": 3500, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "AC", "Kitchen", "Pool"], "wifi_speed_mbps": 150, "photos": _picsum("gulshan-modern"), "created_at": datetime.utcnow()},
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Dhanmondi Lake View Room", "description": "Private room with a beautiful view of Dhanmondi Lake.", "location_city": "Dhaka", "latitude": 23.7465, "longitude": 90.3760, "price_per_night": 1500, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["AC", "Kitchen"], "wifi_speed_mbps": 50, "photos": _picsum("dhanmondi-lake"), "created_at": datetime.utcnow()},
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Banani Shared Workspace", "description": "A budget-friendly shared room for students and backpackers.", "location_city": "Dhaka", "latitude": 23.7925, "longitude": 90.4078, "price_per_night": 800, "has_coworking_space": True, "space_type": "Shared Room", "amenities": ["High-Speed WiFi", "Kitchen"], "wifi_speed_mbps": 100, "photos": _picsum("banani-shared"), "created_at": datetime.utcnow()},

            # Chittagong (3)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Agrabad Business Suite", "description": "Private room perfect for business travelers.", "location_city": "Chittagong", "latitude": 22.3333, "longitude": 91.8333, "price_per_night": 2000, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "AC"], "wifi_speed_mbps": 80, "photos": _picsum("agrabad-suite"), "created_at": datetime.utcnow()},
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Foy's Lake Cottage", "description": "A beautiful cottage near Foy's Lake.", "location_city": "Chittagong", "latitude": 22.3667, "longitude": 91.8000, "price_per_night": 2500, "has_coworking_space": False, "space_type": "Full Apartment", "amenities": ["Kitchen", "Parking"], "wifi_speed_mbps": 40, "photos": _picsum("foys-lake-cottage"), "created_at": datetime.utcnow()},
            {"host_id": "ctg03", "host_name": "Rina Das", "host_email": "rina@email.com", "host_phone": "01711112222", "host_nid": "1993030303030", "space_title": "GEC Circle Cozy Room", "description": "A small and cozy room in the GEC Circle area.", "location_city": "Chittagong", "latitude": 22.3592, "longitude": 91.8217, "price_per_night": 1100, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["AC"], "wifi_speed_mbps": 45, "photos": _picsum("gec-circle"), "created_at": datetime.utcnow()},

            # Cox's Bazar (2)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Sea Pearl Shared Room", "description": "Affordable shared room with a direct view of the beach.", "location_city": "Cox's Bazar", "latitude": 21.4272, "longitude": 92.0058, "price_per_night": 1000, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["AC"], "wifi_speed_mbps": 30, "photos": _picsum("cox-sea-pearl"), "created_at": datetime.utcnow()},
            {"host_id": "cox02", "host_name": "Jannat Ferdous", "host_email": "jannat@email.com", "host_phone": "01812345678", "host_nid": "1991010101010", "space_title": "Inani Beach House", "description": "A full beach house right on Inani Beach.", "location_city": "Cox's Bazar", "latitude": 21.2222, "longitude": 92.0425, "price_per_night": 5000, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["Kitchen", "Parking", "High-Speed WiFi"], "wifi_speed_mbps": 70, "photos": _picsum("inani-beach"), "created_at": datetime.utcnow()},

            # Sylhet (2)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Jaflong Nature Retreat", "description": "A peaceful private room surrounded by nature.", "location_city": "Sylhet", "latitude": 25.1639, "longitude": 92.0144, "price_per_night": 1300, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Kitchen", "Parking"], "wifi_speed_mbps": 25, "photos": _picsum("jaflong-retreat"), "created_at": datetime.utcnow()},
            {"host_id": "syl03", "host_name": "Peter Das", "host_email": "peter@email.com", "host_phone": "01612345678", "host_nid": "1988080808080", "space_title": "Zindabazar Apartment", "description": "An apartment in the busiest part of Sylhet.", "location_city": "Sylhet", "latitude": 24.8949, "longitude": 91.8687, "price_per_night": 2200, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "AC", "Kitchen"], "wifi_speed_mbps": 100, "photos": _picsum("zindabazar"), "created_at": datetime.utcnow()},

            # Sreemangal (2)
            {"host_id": "nomad#1", "host_name": "Mike Milan", "host_email": "milan@mike.com", "host_phone": "01987234561", "host_nid": "213564789986", "space_title": "Sreemangal Tea Estate Bungalow", "description": "An entire bungalow inside a tea garden.", "location_city": "Sreemangal", "latitude": 24.3069, "longitude": 91.7292, "price_per_night": 4000, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "Kitchen", "Parking"], "wifi_speed_mbps": 60, "photos": _picsum("sreemangal-bungalow"), "created_at": datetime.utcnow()},
            {"host_id": "syl04", "host_name": "Nisha Deb", "host_email": "nisha@email.com", "host_phone": "01511223344", "host_nid": "1995050505050", "space_title": "Lawachara Forest Cabin", "description": "A rustic cabin on the edge of Lawachara National Park.", "location_city": "Sreemangal", "latitude": 24.3167, "longitude": 91.7833, "price_per_night": 1800, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 20, "photos": _picsum("lawachara-cabin"), "created_at": datetime.utcnow()},

            # Khulna (2)
            {"host_id": "khl01", "host_name": "Mizanur Rahman", "host_email": "mizanur@email.com", "host_phone": "01199999999", "host_nid": "1987060606060", "space_title": "Sundarbans Eco Hut", "description": "A rustic shared hut for nature lovers.", "location_city": "Khulna", "latitude": 22.8167, "longitude": 89.5500, "price_per_night": 700, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 20, "photos": _picsum("sundarbans-hut"), "created_at": datetime.utcnow()},
            {"host_id": "khl02", "host_name": "Afia Sultana", "host_email": "afia@email.com", "host_phone": "01987654321", "host_nid": "1990121212121", "space_title": "City Center Apartment", "description": "A modern apartment in the heart of Khulna.", "location_city": "Khulna", "latitude": 22.8153, "longitude": 89.5663, "price_per_night": 1800, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["High-Speed WiFi", "AC"], "wifi_speed_mbps": 90, "photos": _picsum("khulna-center"), "created_at": datetime.utcnow()},

            # Rajshahi (2)
            {"host_id": "raj01", "host_name": "Ayesha Siddika", "host_email": "ayesha@email.com", "host_phone": "01010101010", "host_nid": "1996070707070", "space_title": "Padma River View Apartment", "description": "Full apartment with a view of the Padma river.", "location_city": "Rajshahi", "latitude": 24.3667, "longitude": 88.6000, "price_per_night": 2200, "has_coworking_space": False, "space_type": "Full Apartment", "amenities": ["AC", "Kitchen", "Parking"], "wifi_speed_mbps": 45, "photos": _picsum("padma-view"), "created_at": datetime.utcnow()},
            {"host_id": "raj02", "host_name": "Imran Mahmud", "host_email": "imran@email.com", "host_phone": "01711223344", "host_nid": "1985050505050", "space_title": "University Area Private Room", "description": "A quiet and clean private room near Rajshahi University.", "location_city": "Rajshahi", "latitude": 24.3745, "longitude": 88.6042, "price_per_night": 1200, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "Kitchen"], "wifi_speed_mbps": 60, "photos": _picsum("rajshahi-uni"), "created_at": datetime.utcnow()},
            
            # Barisal (2)
            {"host_id": "bar01", "host_name": "Farhan Islam", "host_email": "farhan@email.com", "host_phone": "01231231231", "host_nid": "1994080808080", "space_title": "Barisal City Center Room", "description": "A convenient private room in the city center.", "location_city": "Barisal", "latitude": 22.7010, "longitude": 90.3535, "price_per_night": 900, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "AC"], "wifi_speed_mbps": 70, "photos": _picsum("barisal-center"), "created_at": datetime.utcnow()},
            {"host_id": "bar02", "host_name": "Shila Rani", "host_email": "shila@email.com", "host_phone": "01811223344", "host_nid": "1992020202020", "space_title": "Riverside Guesthouse", "description": "A guesthouse with a beautiful view of the river.", "location_city": "Barisal", "latitude": 22.7010, "longitude": 90.3535, "price_per_night": 1400, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 30, "photos": _picsum("barisal-river"), "created_at": datetime.utcnow()},

            # Rangpur (2)
            {"host_id": "ran01", "host_name": "Ishita Roy", "host_email": "ishita@email.com", "host_phone": "01451451451", "host_nid": "1997090909090", "space_title": "Rangpur Quiet Corner", "description": "A quiet shared room for focused work.", "location_city": "Rangpur", "latitude": 25.7439, "longitude": 89.2752, "price_per_night": 600, "has_coworking_space": True, "space_type": "Shared Room", "amenities": ["High-Speed WiFi"], "wifi_speed_mbps": 90, "photos": _picsum("rangpur-quiet"), "created_at": datetime.utcnow()},
            {"host_id": "ran02", "host_name": "Asif Iqbal", "host_email": "asif@email.com", "host_phone": "01911223344", "host_nid": "1990101010101", "space_title": "Modern Studio Apartment", "description": "A fully furnished studio apartment in Rangpur.", "location_city": "Rangpur", "latitude": 25.7439, "longitude": 89.2752, "price_per_night": 1600, "has_coworking_space": True, "space_type": "Full Apartment", "amenities": ["AC", "Kitchen", "High-Speed WiFi"], "wifi_speed_mbps": 80, "photos": _picsum("rangpur-studio"), "created_at": datetime.utcnow()},

            # Mymensingh (2)
            {"host_id": "mym01", "host_name": "Rashed Kabir", "host_email": "rashed@email.com", "host_phone": "01671671671", "host_nid": "1986101010101", "space_title": "Brahmaputra Riverside Apartment", "description": "Enjoy the view of the Brahmaputra river.", "location_city": "Mymensingh", "latitude": 24.7471, "longitude": 90.4203, "price_per_night": 1600, "has_coworking_space": False, "space_type": "Full Apartment", "amenities": ["Kitchen", "Parking"], "wifi_speed_mbps": 35, "photos": _picsum("brahmaputra-apt"), "created_at": datetime.utcnow()},
            {"host_id": "mym02", "host_name": "Farida Yasmin", "host_email": "farida@email.com", "host_phone": "01311223344", "host_nid": "1989090909090", "space_title": "Agricultural University Guest Room", "description": "A private room for visitors to the Agricultural University.", "location_city": "Mymensingh", "latitude": 24.7269, "longitude": 90.4325, "price_per_night": 950, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi"], "wifi_speed_mbps": 55, "photos": _picsum("mymensingh-uni"), "created_at": datetime.utcnow()},

            # Gazipur (2)
            {"host_id": "gaz01", "host_name": "Tania Rahman", "host_email": "tania@email.com", "host_phone": "01987654321", "host_nid": "1993111111111", "space_title": "Gazipur Industrial Hub Room", "description": "Private room for professionals working in Gazipur.", "location_city": "Gazipur", "latitude": 24.0958, "longitude": 90.4125, "price_per_night": 1100, "has_coworking_space": True, "space_type": "Private Room", "amenities": ["High-Speed WiFi", "AC", "Parking"], "wifi_speed_mbps": 110, "photos": _picsum("gazipur-hub"), "created_at": datetime.utcnow()},
            {"host_id": "gaz02", "host_name": "Karim Sheikh", "host_email": "karim@email.com", "host_phone": "01712345678", "host_nid": "1984040404040", "space_title": "Bhawal National Park Resthouse", "description": "A quiet resthouse near Bhawal National Park.", "location_city": "Gazipur", "latitude": 24.0958, "longitude": 90.4125, "price_per_night": 2000, "has_coworking_space": False, "space_type": "Full Apartment", "amenities": ["Kitchen", "Parking"], "wifi_speed_mbps": 30, "photos": _picsum("bhawal-park"), "created_at": datetime.utcnow()},

            # Bandarban (2)
            {"host_id": "ban01", "host_name": "David Tripura", "host_email": "david.t@email.com", "host_phone": "01515151515", "host_nid": "1999030303030", "space_title": "Bandarban Hillside Cabin", "description": "A rustic shared cabin with breathtaking views.", "location_city": "Bandarban", "latitude": 22.1994, "longitude": 92.2185, "price_per_night": 1500, "has_coworking_space": False, "space_type": "Shared Room", "amenities": ["Kitchen"], "wifi_speed_mbps": 15, "photos": _picsum("bandarban-cabin"), "created_at": datetime.utcnow()},
            {"host_id": "ban02", "host_name": "Maria Marma", "host_email": "maria@email.com", "host_phone": "01812345678", "host_nid": "1998080808080", "space_title": "Nilgiri Mountain View", "description": "A room with a stunning view of the Nilgiri mountains.", "location_city": "Bandarban", "latitude": 21.9558, "longitude": 92.3236, "price_per_night": 2500, "has_coworking_space": False, "space_type": "Private Room", "amenities": ["Parking"], "wifi_speed_mbps": 10, "photos": _picsum("nilgiri-view"), "created_at": datetime.utcnow()},
        ]
        spaces_collection.insert_many(sample_data)
        print(f"{len(sample_data)} sample spaces added.")


def reset_sample_spaces():
    """Danger: deletes all spaces, then repopulates with sample data."""
    deleted = spaces_collection.delete_many({}).deleted_count
    print(f"Deleted {deleted} existing spaces. Reinserting samples...")
    add_sample_spaces()
