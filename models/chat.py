from datetime import datetime
from flask import current_app
from models.user import db
try:
    from bson import ObjectId
except Exception:
    ObjectId = None

def _to_objid(v):
    if v is None:
        return None
    if ObjectId is None:
        return v
    try:
        if isinstance(v, ObjectId):
            return v
        return ObjectId(str(v))
    except Exception:
        return v

def _get_db():
    return db

# New: try to resolve a user's display name from the users collection (robust to different field names)
def get_user_display_name(user_identifier):
    """
    Return a friendly display name for a user id/identifier.
    Prefer first_name + last_name, then username/display_name/name/full_name, fall back to id.
    """
    db = _get_db()
    if not user_identifier:
        return "Unknown"
    try:
        candidates = []
        oid = _to_objid(user_identifier)
        if oid is not None:
            candidates.append({"_id": oid})
        candidates += [{"id": user_identifier}, {"user_id": user_identifier}, {"username": user_identifier}, {"email": user_identifier}]
        user = db.users.find_one({"$or": candidates})
        if not user:
            user = db.users.find_one({}, {"first_name":1,"last_name":1,"username":1,"name":1,"display_name":1})
        if not user:
            return str(user_identifier)
        # prefer first + last
        fn = user.get("first_name") or user.get("fname") or user.get("given_name")
        ln = user.get("last_name") or user.get("lname") or user.get("family_name")
        if fn:
            if ln:
                return f"{fn} {ln}"
            return str(fn)
        for f in ("username", "display_name", "name", "full_name", "id"):
            if f in user and user.get(f):
                return str(user.get(f))
        return str(user.get("_id") or user_identifier)
    except Exception:
        current_app.logger.exception("get_user_display_name failed for %s", user_identifier)
        return str(user_identifier)

def get_space_title(space_identifier):
    """
    Return human-friendly space title/name for a given space id.
    Tries _id/ObjectId and string id fields. Falls back to str(space_identifier).
    """
    db = _get_db()
    if space_identifier is None:
        return None
    try:
        q = []
        oid = _to_objid(space_identifier)
        if oid is not None:
            q.append({"_id": oid})
        q += [{"id": space_identifier}, {"space_id": space_identifier}, {"_id": space_identifier}]
        space = db.spaces.find_one({"$or": q})
        if not space:
            return str(space_identifier)
        # common title fields
        for f in ("title", "space_title", "name"):
            if f in space and space.get(f):
                return str(space.get(f))
        return str(space.get("_id") or space_identifier)
    except Exception:
        current_app.logger.exception("get_space_title failed for %s", space_identifier)
        return str(space_identifier)

def enrich_messages_with_sender_names(messages):
    """
    Add 'sender_name' (string), normalize 'sender_id', and format 'created_at' on each message.
    """
    for m in messages:
        try:
            # resolve sender id
            sid = None
            if isinstance(m, dict):
                sid = m.get("sender_id") or m.get("sender")
            else:
                sid = getattr(m, "sender_id", None) or getattr(m, "sender", None)

            # resolve display name
            name = get_user_display_name(sid)
            # format created_at to readable string
            created = None
            if isinstance(m, dict):
                created = m.get("created_at")
            else:
                created = getattr(m, "created_at", None)

            if isinstance(created, datetime):
                created_str = created.strftime("%b %d, %Y %I:%M %p")  # e.g. "Aug 27, 2025 04:21 PM"
            else:
                # attempt parsing string or fallback to raw string
                try:
                    created_dt = datetime.fromisoformat(str(created))
                    created_str = created_dt.strftime("%b %d, %Y %I:%M %p")
                except Exception:
                    created_str = str(created) if created is not None else ""

            # attach normalized fields
            if isinstance(m, dict):
                m["sender_name"] = name
                m["sender_id"] = str(sid) if sid is not None else None
                m["created_at"] = created_str
            else:
                try:
                    setattr(m, "sender_name", name)
                except Exception:
                    pass
                try:
                    setattr(m, "created_at", created_str)
                except Exception:
                    pass
        except Exception:
            current_app.logger.exception("Failed to enrich message sender for %s", repr(m))
    return messages

def get_or_create_conversation(host_id, traveler_id, space_id=None):
    db = _get_db()
    host_oid = _to_objid(host_id)
    trav_oid = _to_objid(traveler_id)
    space_oid = _to_objid(space_id) if space_id is not None else None

    query = {"host_id": host_oid, "traveler_id": trav_oid, "space_id": space_oid}

    try:
        conv = db.conversations.find_one(query)
        if conv:
            current_app.logger.debug("Found existing conversation %s", conv.get("_id"))
            return conv

        now = datetime.utcnow()
        conv_doc = {
            "host_id": host_oid,
            "traveler_id": trav_oid,
            "space_id": space_oid,
            "created_at": now,
            "last_message_at": None
        }
        res = db.conversations.insert_one(conv_doc)
        conv = db.conversations.find_one({"_id": res.inserted_id})
        current_app.logger.info("Created conversation %s for host=%s traveler=%s space=%s", res.inserted_id, host_oid, trav_oid, )
        return conv
    except Exception as e:
        current_app.logger.exception("get_or_create_conversation failed: %s", e)
        raise

def add_message(conversation_id, sender_id, body):
    db = _get_db()
    conv_oid = _to_objid(conversation_id)
    sender_oid = _to_objid(sender_id)
    now = datetime.utcnow()
    msg = {
        "conversation_id": conv_oid,
        "sender_id": sender_oid,
        "body": body,
        "created_at": now
    }
    try:
        res = db.messages.insert_one(msg)
        # Try to update last_message_at on the conversation; ignore if update misses
        try:
            db.conversations.update_one({"_id": conv_oid}, {"$set": {"last_message_at": now}})
        except Exception:
            current_app.logger.debug("Could not update last_message_at for conversation %s", conv_oid)
        msg["_id"] = res.inserted_id
        current_app.logger.info("Inserted message %s into conversation %s (sender=%s)", res.inserted_id, conv_oid, sender_oid)
        return msg
    except Exception as e:
        current_app.logger.exception("Failed to insert message: %s", e)
        raise

def find_conversations_for_user(user_id):
    db = _get_db()
    uid = _to_objid(user_id)
    try:
        return list(db.conversations.find({"$or": [{"host_id": uid}, {"traveler_id": uid}]}).sort("last_message_at", -1))
    except Exception as e:
        current_app.logger.exception("find_conversations_for_user failed: %s", e)
        return []

def get_conversation_by_id(conv_id):
    db = _get_db()
    conv_oid = _to_objid(conv_id)
    try:
        return db.conversations.find_one({"_id": conv_oid})
    except Exception as e:
        current_app.logger.exception("get_conversation_by_id failed: %s", e)
        return None

def get_messages_for_conversation(conv_id):
    db = _get_db()
    conv_oid = _to_objid(conv_id)
    try:
        return list(db.messages.find({"conversation_id": conv_oid}).sort("created_at", 1))
    except Exception as e:
        current_app.logger.exception("get_messages_for_conversation failed: %s", e)
        return []
        
# --------------- Admin Messages ---------------

def get_or_create_admin_conversation(user_id):
    """
    Create or find an existing conversation between a user and admin
    """
    db = _get_db()
    user_oid = _to_objid(user_id)
    
    query = {"user_id": user_oid, "type": "admin_message"}
    
    try:
        conv = db.admin_conversations.find_one(query)
        if conv:
            current_app.logger.debug("Found existing admin conversation %s", conv.get("_id"))
            return conv
            
        now = datetime.utcnow()
        conv_doc = {
            "user_id": user_oid,
            "type": "admin_message",
            "created_at": now,
            "last_message_at": None,
            "unread_by_admin": False,
            "unread_by_user": False
        }
        res = db.admin_conversations.insert_one(conv_doc)
        conv = db.admin_conversations.find_one({"_id": res.inserted_id})
        current_app.logger.info("Created admin conversation %s for user=%s", res.inserted_id, user_oid)
        return conv
    except Exception as e:
        current_app.logger.exception("get_or_create_admin_conversation failed: %s", e)
        raise

def add_admin_message(conversation_id, sender_id, body):
    """
    Add a message to an admin conversation and update unread flags
    """
    db = _get_db()
    conv_oid = _to_objid(conversation_id)
    sender_oid = _to_objid(sender_id)
    now = datetime.utcnow()
    
    msg = {
        "conversation_id": conv_oid,
        "sender_id": sender_oid,
        "body": body,
        "created_at": now
    }
    
    try:
        res = db.admin_messages.insert_one(msg)
        
        # Update conversation with last_message_at and set unread flags
        update_data = {"last_message_at": now}
        
        # Set unread flags based on sender
        if sender_id == "ADMIN":
            update_data["unread_by_admin"] = False
            update_data["unread_by_user"] = True
        else:
            update_data["unread_by_admin"] = True
            update_data["unread_by_user"] = False
            
        db.admin_conversations.update_one({"_id": conv_oid}, {"$set": update_data})
            
        msg["_id"] = res.inserted_id
        current_app.logger.info("Inserted admin message %s into conversation %s (sender=%s)", 
                               res.inserted_id, conv_oid, sender_oid)
        return msg
    except Exception as e:
        current_app.logger.exception("Failed to insert admin message: %s", e)
        raise

def find_admin_conversations():
    """
    Find all conversations between users and admin
    """
    db = _get_db()
    try:
        return list(db.admin_conversations.find({"type": "admin_message"}).sort("last_message_at", -1))
    except Exception as e:
        current_app.logger.exception("find_admin_conversations failed: %s", e)
        return []

def find_host_conversations(host_id):
    """
    Find all conversations between users and a specific host
    """
    db = _get_db()
    host_oid = _to_objid(host_id)
    try:
        return list(db.admin_conversations.find({
            "host_id": host_oid,
            "type": "host_message"
        }).sort("last_message_at", -1))
    except Exception as e:
        current_app.logger.exception(f"find_host_conversations failed: {e}")
        return []

def find_user_host_conversations(user_id):
    """
    Find all conversations between a user and any hosts
    """
    db = _get_db()
    user_oid = _to_objid(user_id)
    try:
        return list(db.admin_conversations.find({
            "user_id": user_oid,
            "type": "host_message"
        }).sort("last_message_at", -1))
    except Exception as e:
        current_app.logger.exception(f"find_user_host_conversations failed: {e}")
        return []

def get_admin_conversation_for_user(user_id):
    """
    Get the admin conversation for a specific user
    """
    db = _get_db()
    user_oid = _to_objid(user_id)
    try:
        return db.admin_conversations.find_one({"user_id": user_oid, "type": "admin_message"})
    except Exception as e:
        current_app.logger.exception("get_admin_conversation_for_user failed: %s", e)
        return None
        
def get_or_create_host_conversation(user_id, host_id, space_id=None):
    """
    Create or find an existing conversation between a user and host
    """
    db = _get_db()
    user_oid = _to_objid(user_id)
    host_oid = _to_objid(host_id)
    space_oid = _to_objid(space_id) if space_id else None
    
    query = {
        "user_id": user_oid,
        "host_id": host_oid,
        "type": "host_message"
    }
    
    if space_oid:
        query["space_id"] = space_oid
    
    try:
        conv = db.admin_conversations.find_one(query)
        if conv:
            current_app.logger.debug("Found existing host conversation %s", conv.get("_id"))
            return conv
            
        now = datetime.utcnow()
        conv_doc = {
            "user_id": user_oid,
            "host_id": host_oid,
            "space_id": space_oid,
            "type": "host_message",
            "created_at": now,
            "last_message_at": None,
            "unread_by_host": False,
            "unread_by_user": False
        }
        res = db.admin_conversations.insert_one(conv_doc)
        conv = db.admin_conversations.find_one({"_id": res.inserted_id})
        current_app.logger.info("Created host conversation %s for user=%s host=%s", res.inserted_id, user_oid, host_oid)
        return conv
    except Exception as e:
        current_app.logger.exception("get_or_create_host_conversation failed: %s", e)
        raise

def get_admin_conversation_by_id(conv_id):
    """
    Get an admin conversation by its ID
    """
    db = _get_db()
    conv_oid = _to_objid(conv_id)
    try:
        return db.admin_conversations.find_one({"_id": conv_oid})
    except Exception as e:
        current_app.logger.exception("get_admin_conversation_by_id failed: %s", e)
        return None

def get_admin_messages_for_conversation(conv_id):
    """
    Get all messages for an admin conversation
    """
    db = _get_db()
    conv_oid = _to_objid(conv_id)
    try:
        return list(db.admin_messages.find({"conversation_id": conv_oid}).sort("created_at", 1))
    except Exception as e:
        current_app.logger.exception("get_admin_messages_for_conversation failed: %s", e)
        return []

def mark_admin_messages_as_read(conv_id, is_admin):
    """
    Mark messages as read for either admin or user
    """
    db = _get_db()
    conv_oid = _to_objid(conv_id)
    try:
        if is_admin:
            db.admin_conversations.update_one({"_id": conv_oid}, {"$set": {"unread_by_admin": False}})
        else:
            db.admin_conversations.update_one({"_id": conv_oid}, {"$set": {"unread_by_user": False}})
        return True
    except Exception as e:
        current_app.logger.exception("mark_admin_messages_as_read failed: %s", e)
        return False

# --------------- Complaints ---------------

def create_complaint(user_id, subject, message, contact_info=None, host_id=None, space_id=None):
    """
    Create a new complaint from a user
    """
    db = _get_db()
    user_oid = _to_objid(user_id)
    now = datetime.utcnow()
    
    complaint = {
        "user_id": user_oid,
        "subject": subject,
        "message": message,
        "contact_info": contact_info,
        "created_at": now,
        "resolved": False,
        "resolved_at": None
    }
    
    # Add host and space info if provided
    if host_id:
        complaint["host_id"] = _to_objid(host_id)
    if space_id:
        complaint["space_id"] = _to_objid(space_id)
        
        # If we have a space_id, try to get its title
        try:
            from models.space import get_space_by_id
            space = get_space_by_id(space_id)
            if space:
                complaint["space_title"] = space.get("space_title")
        except Exception as e:
            current_app.logger.exception(f"Failed to get space title for complaint: {e}")
    
    try:
        res = db.complaints.insert_one(complaint)
        complaint["_id"] = res.inserted_id
        current_app.logger.info("Created complaint %s for user %s", res.inserted_id, user_oid)
        return complaint
    except Exception as e:
        current_app.logger.exception("create_complaint failed: %s", e)
        raise
        
def get_complaints_by_host(host_id):
    """
    Get all complaints related to a specific host
    """
    db = _get_db()
    host_oid = _to_objid(host_id)
    try:
        return list(db.complaints.find({"host_id": host_oid}).sort("created_at", -1))
    except Exception as e:
        current_app.logger.exception(f"get_complaints_by_host failed: {e}")
        return []

def get_all_complaints():
    """
    Get all complaints, sorted by creation date (newest first)
    """
    db = _get_db()
    try:
        return list(db.complaints.find().sort("created_at", -1))
    except Exception as e:
        current_app.logger.exception("get_all_complaints failed: %s", e)
        return []

def get_unresolved_complaints():
    """
    Get all unresolved complaints
    """
    db = _get_db()
    try:
        return list(db.complaints.find({"resolved": False}).sort("created_at", -1))
    except Exception as e:
        current_app.logger.exception("get_unresolved_complaints failed: %s", e)
        return []

def get_complaint_by_id(complaint_id):
    """
    Get a complaint by its ID
    """
    db = _get_db()
    complaint_oid = _to_objid(complaint_id)
    try:
        return db.complaints.find_one({"_id": complaint_oid})
    except Exception as e:
        current_app.logger.exception("get_complaint_by_id failed: %s", e)
        return None

def get_complaints_for_user(user_id):
    """
    Get all complaints submitted by a specific user
    """
    db = _get_db()
    user_oid = _to_objid(user_id)
    try:
        return list(db.complaints.find({"user_id": user_oid}).sort("created_at", -1))
    except Exception as e:
        current_app.logger.exception("get_complaints_for_user failed: %s", e)
        return []

def mark_complaint_as_resolved(complaint_id):
    """
    Mark a complaint as resolved
    """
    db = _get_db()
    complaint_oid = _to_objid(complaint_id)
    now = datetime.utcnow()
    
    try:
        db.complaints.update_one(
            {"_id": complaint_oid},
            {"$set": {"resolved": True, "resolved_at": now}}
        )
        current_app.logger.info("Marked complaint %s as resolved", complaint_id)
        return True
    except Exception as e:
        current_app.logger.exception("mark_complaint_as_resolved failed: %s", e)
        return False