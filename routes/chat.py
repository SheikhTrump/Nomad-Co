from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import current_user

chat_bp = Blueprint('chat', __name__, url_prefix='/chat', template_folder='../templates')

def _current_uid():
    # prefer flask-login, otherwise session-based user_id
    if getattr(current_user, "is_authenticated", False):
        return getattr(current_user, "id", getattr(current_user, "_id", None))
    return session.get("user_id")

@chat_bp.route('/conversations')
def conversations():
    uid = _current_uid()
    if not uid:
        flash("Please log in to view conversations.", "warning")
        return redirect(url_for('auth.login'))
    try:
        from models.chat import find_conversations_for_user, get_user_display_name, get_space_title
        convs = find_conversations_for_user(uid)
        # enrich conversations for template
        enriched = []
        for c in convs:
            try:
                host_id = c.get("host_id")
                trav_id = c.get("traveler_id")
                space_id = c.get("space_id")
                host_name = get_user_display_name(host_id)
                trav_name = get_user_display_name(trav_id)
                space_title = get_space_title(space_id) if space_id else None
                # ensure dict (cursor returns dicts)
                c["_host_name"] = host_name
                c["_traveler_name"] = trav_name
                c["_space_title"] = space_title
            except Exception:
                current_app.logger.exception("Failed to enrich conversation %s", c.get("_id"))
            enriched.append(c)
        return render_template('chat/conversations.html', conversations=enriched, uid=uid)
    except Exception:
        current_app.logger.exception("conversations: mongo helper failed")
        return render_template('chat/conversations.html', conversations=[], uid=uid)

@chat_bp.route('/conversations/<conv_id>')
def conversation_detail(conv_id):
    uid = _current_uid()
    if not uid:
        flash("Please log in to view conversation.", "warning")
        return redirect(url_for('auth.login'))
    try:
        from models.chat import get_conversation_by_id, get_messages_for_conversation, enrich_messages_with_sender_names, get_space_title
        conv = get_conversation_by_id(conv_id)
        if not conv:
            flash("Conversation not found.", "warning")
            return redirect(url_for('chat.conversations'))
        # participant check (robust)
        if str(conv.get("host_id")) != str(uid) and str(conv.get("traveler_id")) != str(uid):
            flash("Access denied.", "danger")
            return redirect(url_for('chat.conversations'))
        messages = get_messages_for_conversation(conv_id)
        try:
            messages = enrich_messages_with_sender_names(messages)
        except Exception:
            current_app.logger.exception("Failed to enrich messages with sender names")
        # resolve space title (may be None)
        space_title = None
        try:
            space_title = get_space_title(conv.get("space_id"))
        except Exception:
            current_app.logger.exception("Failed to resolve space title for conv %s", conv_id)
        # pass uid and space_title
        return render_template('chat/detail.html', conversation=conv, messages=messages, uid=uid, space_title=space_title)
    except Exception:
        current_app.logger.exception("conversation_detail: mongo helper failed")
        flash("Could not open conversation.", "danger")
        return redirect(url_for('chat.conversations'))

@chat_bp.route('/conversations/create_with_message', methods=['POST'])
def create_conversation_with_message():
    uid = _current_uid()
    if not uid:
        flash("Please log in to send a message.", "warning")
        return redirect(url_for('auth.login'))

    other_id = request.form.get('other_user_id') or request.form.get('host_id')
    space_id = request.form.get('space_id') or request.form.get('space')
    body = (request.form.get('message') or "").strip()
    if not other_id or not body:
        flash('Please enter a message.', 'warning')
        return redirect(request.referrer or url_for('space_bp.space_detail', space_id=space_id))

    try:
        from models.chat import get_or_create_conversation, add_message
        host_id = other_id
        traveler_id = uid
        conv = get_or_create_conversation(host_id=host_id, traveler_id=traveler_id, space_id=space_id)
        if not conv:
            raise RuntimeError("Failed to create conversation")
        conv_id = conv.get("_id") or conv.get("id")
        msg = add_message(conv_id, traveler_id, body)
        current_app.logger.info("chat: inserted message %s into conv %s", getattr(msg, "_id", msg.get("_id", None)), conv_id)
        flash('Message sent to host.', 'success')
        return redirect(url_for('chat.conversation_detail', conv_id=str(conv_id)))
    except Exception as e:
        current_app.logger.exception("create_conversation_with_message failed: %s", e)
        flash('Could not send message at this time.', 'danger')
        return redirect(request.referrer or url_for('space_bp.space_detail', space_id=space_id))

@chat_bp.route('/conversations/<conv_id>/messages', methods=['POST'])
def post_message(conv_id):
    uid = _current_uid()
    if not uid:
        flash("Please log in to send a message.", "warning")
        return redirect(url_for('auth.login'))

    body = (request.form.get('body') or request.form.get('message') or "").strip()
    if not body:
        flash('Message cannot be empty.', 'warning')
        return redirect(request.referrer or url_for('chat.conversation_detail', conv_id=conv_id))

    try:
        from models.chat import get_conversation_by_id, add_message
        conv = get_conversation_by_id(conv_id)
        if not conv:
            flash('Conversation not found.', 'warning')
            return redirect(url_for('chat.conversations'))
        if str(conv.get('host_id')) != str(uid) and str(conv.get('traveler_id')) != str(uid):
            flash('Access denied.', 'danger')
            return redirect(url_for('chat.conversations'))
        conv_id_real = conv.get("_id") or conv.get("id")
        msg = add_message(conv_id_real, uid, body)
        current_app.logger.info("chat: post_message inserted %s into conv %s", getattr(msg, "_id", msg.get("_id", None)), conv_id_real)
        flash('Message sent.', 'success')
        return redirect(url_for('chat.conversation_detail', conv_id=str(conv_id_real)))
    except Exception as e:
        current_app.logger.exception("post_message failed: %s", e)
        flash('Could not post message.', 'danger')
        return redirect(request.referrer or url_for('chat.conversation_detail', conv_id=conv_id))
        
# ------------- Admin Messaging -------------

@chat_bp.route('/contact-admin')
def contact_admin():
    uid = _current_uid()
    if not uid:
        flash("Please log in to contact admin.", "warning")
        return redirect(url_for('auth.login'))
        
    try:
        from models.chat import get_or_create_admin_conversation, get_admin_messages_for_conversation, enrich_messages_with_sender_names, mark_admin_messages_as_read
        # Get or create a conversation with admin
        conv = get_or_create_admin_conversation(uid)
        if conv:
            # Mark messages as read by user
            mark_admin_messages_as_read(conv.get("_id"), is_admin=False)
            
            # Get messages
            messages = get_admin_messages_for_conversation(conv.get("_id"))
            messages = enrich_messages_with_sender_names(messages)
            return render_template('chat/admin_messages.html', conversation=conv, messages=messages, uid=uid)
        else:
            # No conversation exists yet, show empty form
            return render_template('chat/admin_messages.html', conversation=None, messages=[], uid=uid)
    except Exception as e:
        current_app.logger.exception("contact_admin failed: %s", e)
        flash('Could not load admin messages.', 'danger')
        return redirect(url_for('auth.dashboard'))
        
@chat_bp.route('/contact-host/<host_id>')
def contact_host(host_id):
    uid = _current_uid()
    if not uid:
        flash("Please log in to contact the host.", "warning")
        return redirect(url_for('auth.login'))
    
    space_id = request.args.get('space_id')
    
    try:
        from models.chat import get_or_create_host_conversation, get_admin_messages_for_conversation
        from models.chat import enrich_messages_with_sender_names, mark_admin_messages_as_read
        
        # Get or create a conversation with host
        conv = get_or_create_host_conversation(uid, host_id, space_id)
        if conv:
            # Mark messages as read by user
            mark_admin_messages_as_read(conv.get("_id"), is_admin=False)
            
            # Get messages
            messages = get_admin_messages_for_conversation(conv.get("_id"))
            messages = enrich_messages_with_sender_names(messages)
            
            # Get host and space info
            from models.user import get_user_by_id
            from models.space import get_space_by_id
            
            host = get_user_by_id(host_id) or {}
            host_name = host.get('first_name', '') + ' ' + host.get('last_name', '') 
            if not host_name.strip():
                host_name = host.get('username', 'Host')
                
            space = None
            if space_id:
                space = get_space_by_id(space_id) or {}
                
            return render_template(
                'chat/host_messages.html', 
                conversation=conv, 
                messages=messages, 
                uid=uid,
                host=host,
                host_name=host_name,
                space=space
            )
        else:
            # Error case
            flash('Could not create conversation with host.', 'danger')
            return redirect(url_for('auth.dashboard'))
    except Exception as e:
        current_app.logger.exception(f"contact_host failed: {e}")
        flash('Could not load host messages.', 'danger')
        return redirect(url_for('auth.dashboard'))
        
@chat_bp.route('/start-admin-conversation/<user_id>')
def start_admin_conversation(user_id):
    uid = _current_uid()
    if uid != "ADMIN" and session.get('role') != 'admin':
        flash("Access denied. Admin privileges required.", "danger")
        return redirect(url_for('auth.dashboard'))
    
    try:
        from models.chat import get_or_create_admin_conversation, get_admin_messages_for_conversation, enrich_messages_with_sender_names
        # Create or find conversation with this user
        conv = get_or_create_admin_conversation(user_id)
        if conv:
            # Mark as read by admin
            from models.chat import mark_admin_messages_as_read
            mark_admin_messages_as_read(conv.get("_id"), is_admin=True)
            
            # Get messages
            messages = get_admin_messages_for_conversation(conv.get("_id"))
            messages = enrich_messages_with_sender_names(messages)
            
            # Add user name to conversation
            from models.chat import get_user_display_name
            user_name = get_user_display_name(user_id)
            conv["_user_name"] = user_name
            
            return redirect(url_for('admin.message_detail', conv_id=str(conv.get("_id"))))
        else:
            flash("Could not create conversation with user.", "danger")
            return redirect(url_for('admin.messages'))
    except Exception as e:
        current_app.logger.exception(f"start_admin_conversation failed: {e}")
        flash('Could not start conversation with user.', 'danger')
        return redirect(url_for('admin.messages'))
        
@chat_bp.route('/contact-admin/send', methods=['POST'])
def send_admin_message():
    uid = _current_uid()
    if not uid:
        flash("Please log in to contact admin.", "warning")
        return redirect(url_for('auth.login'))
        
    body = (request.form.get('body') or request.form.get('message') or "").strip()
    if not body:
        flash('Message cannot be empty.', 'warning')
        return redirect(url_for('chat.contact_admin'))
        
    try:
        from models.chat import get_or_create_admin_conversation, add_admin_message
        
        # Get conversation ID from form if provided
        conv_id_form = request.form.get('conv_id', '')
        
        # Get or create admin conversation
        conv = get_or_create_admin_conversation(uid)
        if not conv:
            raise RuntimeError("Failed to create admin conversation")
            
        conv_id = conv.get("_id") or conv.get("id")
        msg = add_admin_message(conv_id, uid, body)
        
        current_app.logger.info("chat: send_admin_message inserted %s", getattr(msg, "_id", msg.get("_id", None)))
        flash('Message sent to admin.', 'success')
        return redirect(url_for('chat.contact_admin'))
    except Exception as e:
        current_app.logger.exception("send_admin_message failed: %s", e)
        flash('Could not send message to admin.', 'danger')
        return redirect(url_for('chat.contact_admin'))
        
@chat_bp.route('/host/send', methods=['POST'])
def send_host_message():
    uid = _current_uid()
    if not uid:
        flash("Please log in to message the host.", "warning")
        return redirect(url_for('auth.login'))
        
    body = (request.form.get('body') or "").strip()
    host_id = request.form.get('host_id')
    space_id = request.form.get('space_id')
    
    if not body or not host_id:
        flash('Message cannot be empty and host must be specified.', 'warning')
        return redirect(url_for('auth.dashboard'))
        
    try:
        from models.chat import get_or_create_host_conversation, add_admin_message
        
        # Get or create host conversation
        conv = get_or_create_host_conversation(uid, host_id, space_id)
        if not conv:
            raise RuntimeError("Failed to create host conversation")
            
        conv_id = conv.get("_id") or conv.get("id")
        msg = add_admin_message(conv_id, uid, body)
        
        current_app.logger.info(f"chat: send_host_message inserted {getattr(msg, '_id', msg.get('_id', None))}")
        flash('Message sent to host.', 'success')
        return redirect(url_for('chat.contact_host', host_id=host_id, space_id=space_id))
    except Exception as e:
        current_app.logger.exception(f"send_host_message failed: {e}")
        flash('Could not send message to host.', 'danger')
        return redirect(url_for('auth.dashboard'))

# ------------- Host Conversations -------------

@chat_bp.route('/host-conversations')
def host_conversations():
    uid = _current_uid()
    if not uid:
        flash("Please log in to view conversations.", "warning")
        return redirect(url_for('auth.login'))
        
    try:
        from models.chat import find_user_host_conversations, enrich_messages_with_sender_names
        from models.space import get_space_by_id
        from models.user import get_user_by_id
        
        # Get all conversations with hosts
        conversations = find_user_host_conversations(uid)
        
        # Enrich conversations with host names and space details
        for conv in conversations:
            host_id = conv.get('host_id')
            space_id = conv.get('space_id')
            
            # Get host info
            host = get_user_by_id(host_id) or {}
            host_name = host.get('first_name', '') + ' ' + host.get('last_name', '')
            if not host_name.strip():
                host_name = host.get('username', 'Host')
            conv['host_name'] = host_name
            
            # Get space info if available
            if space_id:
                space = get_space_by_id(space_id) or {}
                conv['space_title'] = space.get('space_title', 'Unknown Space')
        
        return render_template('chat/host_conversations.html', conversations=conversations)
    except Exception as e:
        current_app.logger.exception(f"host_conversations failed: {e}")
        flash('Could not load host conversations.', 'danger')
        return redirect(url_for('auth.dashboard'))

# ------------- Complaints -------------

@chat_bp.route('/submit-complaint')
def submit_complaint_form():
    uid = _current_uid()
    if not uid:
        flash("Please log in to submit a complaint.", "warning")
        return redirect(url_for('auth.login'))
    
    # Get host_id and space_id from query params if provided
    host_id = request.args.get('host_id')
    space_id = request.args.get('space_id')
        
    # Show complaint form
    return render_template('chat/complaint_form.html', host_id=host_id, space_id=space_id)
    
@chat_bp.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    uid = _current_uid()
    if not uid:
        flash("Please log in to submit a complaint.", "warning")
        return redirect(url_for('auth.login'))
        
    subject = (request.form.get('subject') or "").strip()
    message = (request.form.get('message') or "").strip()
    contact_info = (request.form.get('contact_info') or "").strip()
    host_id = request.form.get('host_id')
    space_id = request.form.get('space_id')
    
    if not subject or not message:
        flash('Subject and message are required.', 'warning')
        return redirect(url_for('chat.submit_complaint_form'))
        
    try:
        from models.chat import create_complaint
        
        complaint_data = {
            "user_id": uid,
            "subject": subject,
            "message": message,
            "contact_info": contact_info
        }
        
        # Add host and space info if provided
        if host_id:
            complaint_data["host_id"] = host_id
        if space_id:
            complaint_data["space_id"] = space_id
            
            # Get space details to include in the complaint
            from models.space import get_space_by_id
            space = get_space_by_id(space_id)
            if space:
                complaint_data["space_title"] = space.get("space_title")
        
        # Create complaint with enhanced data
        complaint = create_complaint(uid, subject, message, contact_info, host_id, space_id)
        
        flash('Your complaint has been submitted successfully.', 'success')
        return redirect(url_for('chat.my_complaints'))
    except Exception as e:
        current_app.logger.exception("submit_complaint failed: %s", e)
        flash('Could not submit complaint.', 'danger')
        return redirect(url_for('chat.submit_complaint_form'))
        
@chat_bp.route('/my-complaints')
def my_complaints():
    uid = _current_uid()
    if not uid:
        flash("Please log in to view your complaints.", "warning")
        return redirect(url_for('auth.login'))
        
    try:
        from models.chat import get_complaints_for_user
        complaints = get_complaints_for_user(uid)
        return render_template('chat/my_complaints.html', complaints=complaints)
    except Exception as e:
        current_app.logger.exception("my_complaints failed: %s", e)
        flash('Could not load your complaints.', 'danger')
        return redirect(url_for('auth.dashboard'))