import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bson.objectid import ObjectId
from models.user import db

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/admin")

@admin_bp.route("/verifications")
def verifications():
    pending_hosts = list(db.users.find({"role": "host", "verification.status": "pending"}))
    for host in pending_hosts:
        nid_path = host.get("verification", {}).get("nid_photo")
        own_path = host.get("verification", {}).get("own_photo")
        host["nid_exists"] = os.path.exists(nid_path) if nid_path else False
        host["own_exists"] = os.path.exists(own_path) if own_path else False
    return render_template("dashboard.html", pending_hosts=pending_hosts)

@admin_bp.route("/verify_host/<user_id>", methods=["POST"])
def verify_host(user_id):
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_verified": True, "verification.status": "approved"}}
    )
    flash("Host verified!", "success")
    return redirect(url_for("admin_bp.verifications"))

@admin_bp.route('/dashboard')
def dashboard():
    dashboard_data = {}
    if session.get('role') == 'admin':
        dashboard_data['pending_hosts'] = list(db.users.find({
            "role": "host",
            "verification.status": "pending"
        }))
    if 'user_id' in session:
        dashboard_data['user'] = db.users.find_one({'_id': ObjectId(session['user_id'])})
    return render_template('dashboard.html', **dashboard_data)