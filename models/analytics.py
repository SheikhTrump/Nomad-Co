# models/analytics.py
# Ei file ta analytics dashboard er jonno database theke shob data query kore
# ebong calculation kore anar logic rakhe.

from .user import db
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import uuid

def get_user_overview():
    """Total user, traveler, ebong host er shongkha calculate kore."""
    total_users = db.users.count_documents({})
    traveler_count = db.users.count_documents({"role": "traveler"})
    host_count = db.users.count_documents({"role": "host"})
    return {
        "total_users": total_users,
        "traveler_count": traveler_count,
        "host_count": host_count
    }

def get_booking_overview():
    """Total booking, total revenue ebong city-wise booking er hishab kore."""
    # Ei function ta ekhon ar beshi use hoy na, `get_advanced_analytics` e
    # aro efficient bhabe kaj kora hoyeche.
    total_bookings = db.bookings.count_documents({})
    
    total_revenue = 0
    city_counts = {}
    all_bookings = list(db.bookings.find({}))

    for booking in all_bookings:
        try:
            # Safely handle both string and datetime objects
            check_in_str = booking.get('check_in_date')
            if isinstance(check_in_str, datetime):
                check_in = check_in_str
            else:
                check_in = datetime.strptime(check_in_str, '%Y-%m-%d')

            check_out_str = booking.get('check_out_date')
            if isinstance(check_out_str, datetime):
                check_out = check_out_str
            else:
                check_out = datetime.strptime(check_out_str, '%Y-%m-%d')
            
            duration = (check_out - check_in).days
            price = float(booking.get('price_per_night', 0))
            total_revenue += duration * price
            
            space_id = booking.get('space_id')
            if space_id:
                space = db.spaces.find_one({'_id': ObjectId(space_id)})
                if space:
                    city = space.get('location_city')
                    if city:
                        city_counts[city] = city_counts.get(city, 0) + 1
        except (ValueError, TypeError, KeyError) as e:
            print(f"Skipping booking due to data error: {e}")
            continue
            
    return {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "city_distribution": city_counts
    }


def get_advanced_analytics():
    """Platform er shob important metrics calculate korar jonno aggregation pipeline use kore."""
    
    # --- Active Users (last 30 days) ---
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = db.users.count_documents({"last_login": {"$gte": thirty_days_ago}})

    # --- New Users (this month) ---
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = db.users.count_documents({"created_at": {"$gte": start_of_month}})

    # --- Booking Statistics (using aggregation for efficiency) ---
    booking_stats_pipeline = [
        {"$match": {"status": "Confirmed"}},
        {"$project": {
            "check_in": {"$toDate": "$check_in_date"},
            "check_out": {"$toDate": "$check_out_date"},
            "booked_at": {"$toDate": "$booked_at"},
            "price": {"$toDouble": "$price_per_night"},
            "user_id": "$user_id",
             "host_id": "$host_id"
        }},
        {"$group": {
            "_id": None,
            "total_bookings": {"$sum": 1},
            "total_revenue": {"$sum": {
                "$multiply": ["$price", {"$max": [1, {"$dateDiff": {"startDate": "$check_in", "endDate": "$check_out", "unit": "day"}}]}]
            }},
            "total_duration": {"$sum": {"$dateDiff": {"startDate": "$check_in", "endDate": "$check_out", "unit": "day"}}},
            "total_lead_time": {"$sum": {"$dateDiff": {"startDate": "$booked_at", "endDate": "$check_in", "unit": "day"}}},
            "unique_bookers": {"$addToSet": "$user_id"}
        }},
        {"$project": {
            "_id": 0,
            "total_bookings": 1,
            "total_revenue": 1,
            "total_duration": 1,
            "total_lead_time": 1,
            "unique_booker_count": {"$size": "$unique_bookers"}
        }}
    ]
    booking_stats_result = list(db.bookings.aggregate(booking_stats_pipeline))
    booking_stats = booking_stats_result[0] if booking_stats_result else {
        "total_bookings": 0, "total_revenue": 0, "total_duration": 0, 
        "total_lead_time": 0, "unique_booker_count": 0
    }

    # --- Cancellation Rate ---
    total_bookings = db.bookings.count_documents({})
    cancelled_bookings = db.bookings.count_documents({"status": "Cancelled"})
    booking_stats['cancelled_bookings'] = cancelled_bookings
    
    # --- Repeat Booker Rate ---
    repeat_bookers_pipeline = [
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    repeat_bookers = len(list(db.bookings.aggregate(repeat_bookers_pipeline)))
    repeat_rate = (repeat_bookers / booking_stats['unique_booker_count'] * 100) if booking_stats['unique_booker_count'] > 0 else 0

    # --- Most Booked Spaces ---
    most_booked_pipeline = [
        {"$group": {"_id": "$space_title", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    most_booked_spaces = list(db.bookings.aggregate(most_booked_pipeline))
    
    # --- Revenue by Location ---
    revenue_by_location_pipeline = [
        {"$match": {"status": "Confirmed"}},
        {"$project": {
            "space_id_obj": {"$toObjectId": "$space_id"},
            "revenue": {
                "$multiply": [
                    {"$toDouble": "$price_per_night"},
                    {"$max": [1, {"$dateDiff": {"startDate": {"$toDate": "$check_in_date"}, "endDate": {"$toDate": "$check_out_date"}, "unit": "day"}}]}
                ]
            }
        }},
        {"$lookup": {
            "from": "spaces",
            "localField": "space_id_obj",
            "foreignField": "_id",
            "as": "space_info"
        }},
        {"$unwind": "$space_info"},
        {"$group": {
            "_id": "$space_info.location_city",
            "total_revenue": {"$sum": "$revenue"}
        }},
        {"$sort": {"total_revenue": -1}}
    ]
    revenue_by_location = list(db.bookings.aggregate(revenue_by_location_pipeline))

    # --- Top Locations by Space Count ---
    top_locations_pipeline = [
        {"$group": {"_id": "$location_city", "space_count": {"$sum": 1}}},
        {"$sort": {"space_count": -1}},
        {"$limit": 3}
    ]
    top_locations = list(db.spaces.aggregate(top_locations_pipeline))

    # --- Top Spaces by Average Rating ---
    top_spaces_pipeline = [
        {"$group": {"_id": "$space_id", "average_rating": {"$avg": "$rating"}}},
        {"$sort": {"average_rating": -1}},
        {"$limit": 5},
        {"$lookup": {
            "from": "spaces",
            "localField": "_id",
            "foreignField": "_id",
            "as": "space_details"
        }},
        {"$unwind": "$space_details"},
        {"$project": {"_id": "$space_details.space_title", "average_rating": 1}}
    ]
    top_spaces = list(db.reviews.aggregate(top_spaces_pipeline))
    
    # --- Most Popular Amenities ---
    popular_amenities_pipeline = [
        {"$unwind": "$amenities"},
        {"$group": {"_id": "$amenities", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    popular_amenities = list(db.spaces.aggregate(popular_amenities_pipeline))

    # --- Top 5 Hosts by Revenue ---
    top_hosts_pipeline = [
        {"$match": {"status": "Confirmed"}},
        {"$project": {
            # Conditionally convert host_id, handle invalid formats gracefully
            "host_id_obj": {
                "$cond": {
                    "if": {"$eq": [{"$strLenBytes": "$host_id"}, 24]},
                    "then": {"$toObjectId": "$host_id"},
                    "else": None  # Set to null if it's not a 24-char string
                }
            },
            "booking_revenue": {
                "$multiply": [
                    {"$toDouble": "$price_per_night"},
                    {"$max": [1, {"$dateDiff": {"startDate": {"$toDate": "$check_in_date"}, "endDate": {"$toDate": "$check_out_date"}, "unit": "day"}}]}
                ]
            }
        }},
        # Filter out documents where the host_id was invalid
        {"$match": {"host_id_obj": {"$ne": None}}},
        {"$lookup": {
            "from": "users",
            "localField": "host_id_obj",
            "foreignField": "_id",
            "as": "host_info"
        }},
        {"$unwind": "$host_info"},
        {"$group": {
            "_id": "$host_info.user_id",
            "total_revenue": {"$sum": "$booking_revenue"}
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": 5}
    ]
    top_hosts = list(db.bookings.aggregate(top_hosts_pipeline))

    # Shob data ekta dictionary te return kora hocche.
    return {
        "active_users": active_users,
        "new_users_this_month": new_users_this_month,
        "booking_stats": booking_stats,
        "repeat_booker_rate": repeat_rate,
        "most_booked_spaces": most_booked_spaces,
        "revenue_by_location": revenue_by_location,
        "top_locations": top_locations,
        "top_spaces": top_spaces,
        "popular_amenities": popular_amenities,
        "top_hosts": top_hosts
    }

def get_recent_signups(limit=5):
    """Shobcheye recent sign up kora user der list dey."""
    # 'users' collection theke 'created_at' field er upor base kore sort kora hocche.
    return list(db.users.find().sort("created_at", -1).limit(limit))

def get_recent_bookings(limit=5):
    """Shobcheye recent booking gular list dey."""
    # 'bookings' collection theke 'booked_at' field er upor base kore sort kora hocche.
    return list(db.bookings.find().sort("booked_at", -1).limit(limit))


