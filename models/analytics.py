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
            check_in = datetime.strptime(booking['check_in_date'], '%Y-m-%d')
            check_out = datetime.strptime(booking['check_out_date'], '%Y-%m-%d')
            duration = max(1, (check_out - check_in).days)
            total_revenue += booking.get('price_per_night', 0) * duration
        except (ValueError, TypeError, KeyError):
            continue 

        try:
            # space_id diye 'spaces' collection theke space er details khuje ber kora hocche.
            space = db.spaces.find_one({"_id": ObjectId(booking["space_id"])})
            if space:
                # Jodi location_city na thake, tahole 'Unknown' hishebe dhora hocche.
                city = space.get("location_city", "Unknown")
                city_counts[city] = city_counts.get(city, 0) + 1
        except (TypeError, KeyError):
            continue

    return {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "city_counts": city_counts
    }

def get_advanced_analytics():
    """
    MongoDB aggregation pipeline use kore advanced analytics data calculate kore.
    Eta onek beshi efficient ebong ek sathe onek data process kore.
    """
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # --- Active Users (goto 30 diner moddhe login koreche) ---
    active_users = db.users.count_documents({"last_login": {"$gte": thirty_days_ago}})

    # --- New Users This Month (ei mashe jara sign up koreche) ---
    today = datetime.utcnow()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = db.users.count_documents({"created_at": {"$gte": start_of_month}})
    
    # --- Booking Statistics (Lead time, Duration, Cancellation Rate) ---
    # Ekti pipeline diye booking er shob hishab kora hocche.
    booking_stats_pipeline = [
        {"$match": {"booking_date": {"$exists": True, "$ne": None}}}, # Shudhu booking_date ache emon document neya hocche.
        {"$project": {
            "status": 1,
            # Booking dewa theke check-in porjonto shomoy (lead time).
            "lead_time": {
                "$dateDiff": {
                    "startDate": {"$toDate": "$booking_date"},
                    "endDate": {"$toDate": "$check_in_date"},
                    "unit": "day"
                }
            },
            # Koto din er jonno booking (duration).
            "duration": {
                "$dateDiff": {
                    "startDate": {"$toDate": "$check_in_date"},
                    "endDate": {"$toDate": "$check_out_date"},
                    "unit": "day"
                }
            },
            # Prottekta booking theke total revenue.
             "booking_revenue": {
                "$multiply": [
                    "$price_per_night",
                    {"$max": [1, {"$dateDiff": {"startDate": {"$toDate": "$check_in_date"}, "endDate": {"$toDate": "$check_out_date"}, "unit": "day"}}]}
                ]
            }
        }},
        {"$group": {
            "_id": None, # Shob document er jonno ekta result.
            "total_bookings": {"$sum": 1},
            "total_lead_time": {"$sum": "$lead_time"},
            "total_duration": {"$sum": "$duration"},
            "total_revenue": {"$sum": "$booking_revenue"},
            # Jodi status "Cancelled" hoy, tahole 1 jog hobe.
            "cancelled_bookings": {"$sum": {"$cond": [{"$eq": ["$status", "Cancelled"]}, 1, 0]}}
        }}
    ]
    booking_stats_result = list(db.bookings.aggregate(booking_stats_pipeline))
    booking_stats = booking_stats_result[0] if booking_stats_result else {
        "total_bookings": 0, "total_lead_time": 0, "total_duration": 0,
        "total_revenue": 0, "cancelled_bookings": 0
    }

    # --- Repeat Booker Rate ---
    booker_pipeline = [
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}, # Prottek user koto gulo booking koreche.
        {"$group": {
            "_id": None,
            "total_bookers": {"$sum": 1}, # Total koto jon user booking koreche.
            "repeat_bookers": {"$sum": {"$cond": [{"$gt": ["$count", 1]}, 1, 0]}} # Tar moddhe kotojon 1 bar er beshi koreche.
        }}
    ]
    booker_stats_result = list(db.bookings.aggregate(booker_pipeline))
    repeat_rate = 0
    if booker_stats_result and booker_stats_result[0]['total_bookers'] > 0:
        stats = booker_stats_result[0]
        repeat_rate = (stats['repeat_bookers'] / stats['total_bookers']) * 100

    # --- Most Booked 5 Spaces ---
    most_booked_pipeline = [
        {"$group": {"_id": "$space_title", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    most_booked_spaces = list(db.bookings.aggregate(most_booked_pipeline))

    # --- Revenue by Location ---
    revenue_by_location_pipeline = [
        {
            "$project": {
                "space_id": {"$toObjectId": "$space_id"},
                "booking_revenue": {
                    "$multiply": [
                        "$price_per_night",
                        {"$max": [1, {"$dateDiff": {"startDate": {"$toDate": "$check_in_date"}, "endDate": {"$toDate": "$check_out_date"}, "unit": "day"}}]}
                    ]
                }
            }
        },
        {
            # 'bookings' collection er sathe 'spaces' collection ke join kora hocche.
            "$lookup": {
                "from": "spaces",
                "localField": "space_id",
                "foreignField": "_id",
                "as": "space_details"
            }
        },
        {"$unwind": "$space_details"},
        {
            # Location city onujayi group kore total revenue ber kora hocche.
            "$group": {
                "_id": "$space_details.location_city",
                "total_revenue": {"$sum": "$booking_revenue"}
            }
        },
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

    # --- Top 5 Spaces by Average Rating ---
    top_spaces_pipeline = [
        {"$group": {
            "_id": "$space_id",
            "average_rating": {"$avg": "$rating"}
        }},
        {"$sort": {"average_rating": -1}},
        {"$limit": 5},
        {"$lookup": {
            "from": "spaces",
            "localField": "_id",
            "foreignField": "_id",
            "as": "space_details"
        }},
        {"$unwind": "$space_details"},
        {"$project": {
            "_id": "$space_details.space_title",
            "average_rating": {"$round": ["$average_rating", 1]} # Rating 1 decimal place e round kora hocche.
        }}
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
            "host_id": 1,
            "booking_revenue": {
                "$multiply": [
                    "$price_per_night",
                    {"$max": [1, {"$dateDiff": {"startDate": {"$toDate": "$check_in_date"}, "endDate": {"$toDate": "$check_out_date"}, "unit": "day"}}]}
                ]
            }
        }},
        {"$group": {
            "_id": "$host_id",
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
    # 'bookings' collection theke 'booking_date' field er upor base kore sort kora hocche.
    return list(db.bookings.find().sort("booking_date", -1).limit(limit))

