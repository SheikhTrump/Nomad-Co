# routes/payout.py

from flask import Blueprint, render_template, session, redirect, url_for, flash
from models.payout import get_payout_details

payout_bp = Blueprint('payout', __name__, template_folder='../templates')

@payout_bp.route('/payouts')
def view_payouts():
    if 'user_id' not in session or session.get('role') != 'host':
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    host_id = session['user_id']
    payout_data = get_payout_details(host_id)
    
    return render_template('payout.html', payout_data=payout_data)
