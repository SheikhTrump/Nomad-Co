from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import current_user
import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../templates')

def _is_admin():
    return session.get('role') in ['host', 'admin']

def _current_uid():
    return session.get('user_id', None)

# Host views their messages (only for the current logged-in host)
@admin_bp.route('/messages')
def messages():
    if session.get('role') != 'host':
        flash("Access denied. Host privileges required.", "danger")
        return redirect(url_for('auth.dashboard'))
        
    host_id = _current_uid()
    if not host_id:
        flash("You must be logged in to view your messages.", "danger")
        return redirect(url_for('auth.login'))
        
    try:
        from models.chat import find_host_conversations, get_user_display_name
        convs = find_host_conversations(host_id)
        
        # Enrich conversations with user details
        for c in convs:
            user_id = c.get("user_id")
            try:
                user_name = get_user_display_name(user_id)
                c["_user_name"] = user_name
            except Exception as e:
                current_app.logger.exception(f"Failed to get user name: {e}")
                c["_user_name"] = user_id
                
            # Format the last message time
            last_msg_time = c.get("last_message_at")
            if last_msg_time and isinstance(last_msg_time, datetime.datetime):
                c["_last_message_time"] = last_msg_time.strftime("%b %d, %Y %I:%M %p")
            elif last_msg_time:
                c["_last_message_time"] = str(last_msg_time)
            else:
                c["_last_message_time"] = "No messages"
                
            # Add space info if available
            if c.get("space_id"):
                from models.space import get_space_by_id
                space = get_space_by_id(c.get("space_id"))
                if space:
                    c["space_title"] = space.get("space_title")
                    
        return render_template('admin/host_messages.html', conversations=convs)
    except Exception as e:
        current_app.logger.exception(f"host_messages failed: {e}")
        flash("Could not load messages.", "danger")
        return redirect(url_for('auth.dashboard'))
        
# Host views a specific conversation
@admin_bp.route('/messages/<conv_id>')
def host_message_detail(conv_id):
    if session.get('role') != 'host':
        flash("Access denied. Host privileges required.", "danger")
        return redirect(url_for('auth.dashboard'))
        
    host_id = _current_uid()
    if not host_id:
        flash("You must be logged in to view messages.", "danger")
        return redirect(url_for('auth.login'))
        
    try:
        from models.chat import get_admin_conversation_by_id, get_admin_messages_for_conversation
        from models.chat import enrich_messages_with_sender_names, mark_admin_messages_as_read
        
        conv = get_admin_conversation_by_id(conv_id)
        if not conv:
            flash("Conversation not found.", "warning")
            return redirect(url_for('admin.messages'))
            
        # Security check - hosts can only see their own conversations
        if str(conv.get("host_id")) != str(host_id):
            flash("Access denied. This is not your conversation.", "danger")
            return redirect(url_for('admin.messages'))
            
        # Mark messages as read by host
        mark_admin_messages_as_read(conv_id, is_admin=True)
            
        messages = get_admin_messages_for_conversation(conv_id)
        messages = enrich_messages_with_sender_names(messages)
        
        # Add user name if not already added
        if not conv.get("_user_name"):
            from models.chat import get_user_display_name
            user_id = conv.get("user_id")
            user_name = get_user_display_name(user_id)
            conv["_user_name"] = user_name
            
        # Get space info if available
        space = None
        if conv.get("space_id"):
            from models.space import get_space_by_id
            space = get_space_by_id(conv.get("space_id"))
            
        return render_template(
            'admin/host_message_detail.html', 
            conversation=conv, 
            messages=messages, 
            uid=host_id,
            space=space
        )
    except Exception as e:
        current_app.logger.exception(f"host_message_detail failed: {e}")
        flash("Could not open conversation.", "danger")
        return redirect(url_for('admin.messages'))


# Host replies to a message
@admin_bp.route('/messages/<conv_id>/reply', methods=['POST'])
def host_reply_to_message(conv_id):
    if session.get('role') != 'host':
        flash("Access denied. Host privileges required.", "danger")
        return redirect(url_for('auth.dashboard'))
    
    host_id = _current_uid()
    if not host_id:
        flash("You must be logged in to reply.", "danger")
        return redirect(url_for('auth.login'))
    
    body = (request.form.get('body') or "").strip()
    if not body:
        flash('Message cannot be empty.', 'warning')
        return redirect(url_for('admin.host_message_detail', conv_id=conv_id))
    
    try:
        from models.chat import get_admin_conversation_by_id, add_admin_message
        conv = get_admin_conversation_by_id(conv_id)
        if not conv:
            flash('Conversation not found.', 'warning')
            return redirect(url_for('admin.messages'))
            
        # Security check - hosts can only reply to their own conversations
        if str(conv.get("host_id")) != str(host_id):
            flash("Access denied. This is not your conversation.", "danger")
            return redirect(url_for('admin.messages'))
            
        conv_id_real = conv.get("_id") or conv.get("id")
        # Use the host's ID as the sender
        msg = add_admin_message(conv_id_real, host_id, body)
        current_app.logger.info(f"admin.host_reply_to_message: inserted message {getattr(msg, '_id', msg.get('_id', None))} into conv {conv_id_real}")
        flash('Reply sent.', 'success')
        return redirect(url_for('admin.host_message_detail', conv_id=str(conv_id_real)))
    except Exception as e:
        current_app.logger.exception(f"admin.host_reply_to_message failed: {e}")
        flash('Could not send reply.', 'danger')
        return redirect(url_for('admin.host_message_detail', conv_id=conv_id))

# Admin views complaints
@admin_bp.route('/complaints')
def complaints():
    if not _is_admin():
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for('auth.dashboard'))
    
    try:
        from models.chat import get_all_complaints, get_user_display_name
        # Check if we want filtered complaints
        filter_param = request.args.get('filter', '')
        
        if filter_param == 'resolved':
            all_complaints = list(filter(lambda c: c.get('resolved', False), get_all_complaints()))
        elif filter_param == 'unresolved':
            all_complaints = list(filter(lambda c: not c.get('resolved', False), get_all_complaints()))
        else:
            all_complaints = get_all_complaints()
            
        # enrich complaints with user names
        for complaint in all_complaints:
            user_id = complaint.get("user_id")
            try:
                user_name = get_user_display_name(user_id)
                complaint["_user_name"] = user_name
            except Exception:
                complaint["_user_name"] = user_id
                
        return render_template('admin/complaints.html', complaints=all_complaints)
    except Exception as e:
        current_app.logger.exception(f"admin.complaints: failed: {e}")
        return render_template('admin/complaints.html', complaints=[])

# Admin views a specific complaint
@admin_bp.route('/complaints/<complaint_id>')
def complaint_detail(complaint_id):
    if not _is_admin():
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for('auth.dashboard'))
    
    try:
        from models.chat import get_complaint_by_id, get_user_display_name
        complaint = get_complaint_by_id(complaint_id)
        if not complaint:
            flash("Complaint not found.", "warning")
            return redirect(url_for('admin.complaints'))
            
        # Add user name to complaint
        user_id = complaint.get("user_id")
        try:
            user_name = get_user_display_name(user_id)
            complaint["_user_name"] = user_name
        except Exception:
            complaint["_user_name"] = user_id
            
        return render_template('admin/complaint_detail.html', complaint=complaint)
    except Exception as e:
        current_app.logger.exception(f"admin.complaint_detail: failed: {e}")
        flash("Could not open complaint.", "danger")
        return redirect(url_for('admin.complaints'))

# Mark complaint as resolved
@admin_bp.route('/complaints/<complaint_id>/resolve', methods=['POST'])
def resolve_complaint(complaint_id):
    if not _is_admin():
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for('auth.dashboard'))
    
    try:
        from models.chat import mark_complaint_as_resolved
        mark_complaint_as_resolved(complaint_id)
        flash("Complaint marked as resolved.", "success")
        return redirect(url_for('admin.complaints'))
    except Exception as e:
        current_app.logger.exception(f"admin.resolve_complaint: failed: {e}")
        flash("Could not update complaint status.", "danger")
        return redirect(url_for('admin.complaint_detail', complaint_id=complaint_id))
