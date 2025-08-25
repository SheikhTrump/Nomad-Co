#models\analytics.py

from .user import db
from datetime import datetime
from bson.objectid import ObjectId 

def get_user_overview():
    """Calculates total users and the breakdown by role."""
    total_users = db.users.count_documents({})
    traveler_count = db.users.count_documents({"role": "traveler"})
    host_count = db.users.count_documents({"role": "host"})
    return {
        "total_users": total_users,
        "traveler_count": traveler_count,
        "host_count": host_count
    }

def get_booking_overview():
    """Calculates total bookings, total revenue, and bookings by city."""
    total_bookings = db.bookings.count_documents({})
    
    # Aggregation pipeline to calculate total revenue and bookings per city
    # NOTE: The original pipeline was complex and not used. It's simplified below.
    # A more robust solution would join bookings with spaces.
    
    total_revenue = 0
    city_counts = {}
    all_bookings = list(db.bookings.find({}))

    for booking in all_bookings:
        # Calculate revenue for each booking
        try:
            check_in = datetime.strptime(booking['check_in_date'], '%Y-%m-%d')
            check_out = datetime.strptime(booking['check_out_date'], '%Y-%m-%d')
            # Ensure duration is at least 1 day
            duration = max(1, (check_out - check_in).days)
            total_revenue += booking.get('price_per_night', 0) * duration
        except (ValueError, TypeError, KeyError):
            # Skip bookings with malformed dates or missing price
            continue 

        # Get the location from the related space document
        # This is where the ObjectId was needed
        try:
            space = db.spaces.find_one({"_id": ObjectId(booking['space_id'])})
            if space:
                city = space.get('location_city', 'Unknown')
                city_counts[city] = city_counts.get(city, 0) + 1
        except Exception:
            # Handles cases where space_id might be invalid
            continue

    return {
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "bookings_by_city": city_counts
    }

def get_recent_signups(limit=5):
    """Fetches the most recently registered users."""
    # Sorting by the auto-generated ObjectId which contains a timestamp.
    return list(db.users.find().sort("_id", -1).limit(limit))

def get_recent_bookings(limit=5):
    """Fetches the most recent bookings."""
    # Assumes a 'booked_at' field exists and is a datetime object
    return list(db.bookings.find().sort("booked_at", -1).limit(limit))
