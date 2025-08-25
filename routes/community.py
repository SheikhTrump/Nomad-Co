from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from bson.objectid import ObjectId
from datetime import datetime

community_bp = Blueprint('community', __name__)

def get_db():
    return current_app.mongo.db

@community_bp.route('/forum')
def forum():
    db = get_db()
    posts = list(db.forum_posts.find().sort('created_at', -1))
    for post in posts:
        user = db.users.find_one({'_id': post['user_id']})
        post['user_name'] = f"{user['first_name']} {user['last_name']}" if user else "Anonymous"
        post['user_type'] = user.get('user_type', 'traveler') if user else "unknown"
    return render_template('community/forum.html', posts=posts)

@community_bp.route('/forum/create', methods=['GET', 'POST'])
@login_required
def create_post():
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        post = {
            'title': title,
            'content': content,
            'category': category,
            'user_id': ObjectId(current_user.id),
            'user_type': getattr(current_user, 'user_type', 'traveler'),
            'created_at': datetime.utcnow(),
            'replies': [],
            'views': 0
        }
        db.forum_posts.insert_one(post)
        flash('Post created successfully!', 'success')
        return redirect(url_for('community.forum'))
    return render_template('community/create_post.html')

@community_bp.route('/forum/<post_id>')
def view_post(post_id):
    db = get_db()
    post = db.forum_posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('community.forum'))
    db.forum_posts.update_one({'_id': ObjectId(post_id)}, {'$inc': {'views': 1}})
    user = db.users.find_one({'_id': post['user_id']})
    post['user_name'] = f"{user['first_name']} {user['last_name']}" if user else "Anonymous"
    post['user_type'] = user.get('user_type', 'traveler') if user else "unknown"
    for reply in post.get('replies', []):
        reply_user = db.users.find_one({'_id': reply['user_id']})
        reply['user_name'] = f"{reply_user['first_name']} {reply_user['last_name']}" if reply_user else "Anonymous"
        reply['user_type'] = reply_user.get('user_type', 'traveler') if reply_user else "unknown"
    return render_template('community/post_detail.html', post=post)

@community_bp.route('/forum/<post_id>/reply', methods=['POST'])
@login_required
def reply_to_post(post_id):
    db = get_db()
    content = request.form.get('content')
    reply = {
        'content': content,
        'user_id': ObjectId(current_user.id),
        'user_type': getattr(current_user, 'user_type', 'traveler'),
        'created_at': datetime.utcnow()
    }
    db.forum_posts.update_one({'_id': ObjectId(post_id)}, {'$push': {'replies': reply}})
    flash('Reply added!', 'success')
    return redirect(url_for('community.view_post', post_id=post_id))