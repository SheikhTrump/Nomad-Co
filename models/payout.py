# models/payout.py

from .user import db
from datetime import datetime

# A direct reference to the new, centralized bookings collection
bookings_collection = db.bookings

def get_payout_details(host_id):
    """
    Calculates the total payout for a host by querying the central bookings collection.
    """
    # Find all confirmed bookings where the host_id matches
    host_bookings = list(bookings_collection.find({
        "host_id": host_id,
        "status": "Confirmed"
    }))

    total_payout = 0
    for booking in host_bookings:
        try:
            # Calculate the duration of the stay in days
            check_in = datetime.strptime(booking['check_in_date'], '%Y-%m-%d')
            check_out = datetime.strptime(booking['check_out_date'], '%Y-%m-%d')
            duration_days = (check_out - check_in).days
            
            # Ensure at least one day is counted
            if duration_days <= 0:
                duration_days = 1
            
            # Calculate total for this booking and add it to the payout
            booking_total = booking['price_per_night'] * duration_days
            booking['duration_days'] = duration_days
            booking['booking_total'] = booking_total
            total_payout += booking_total
        except (ValueError, TypeError, KeyError) as e:
            # Handle cases where data might be missing or malformed
            print(f"Could not process booking {booking.get('_id')}: {e}")
            booking['duration_days'] = 'N/A'
            booking['booking_total'] = 'Error'
            
    return {
        "total_payout": total_payout,
        "bookings": host_bookings,
        "booking_count": len(host_bookings)
    }

