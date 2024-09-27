from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, current_app
from flask_security import hash_password, login_required

import logging
from app.models import User, Story, Chapter
from app.story_service import generate_story

logging.basicConfig(level=logging.DEBUG)

routes_bp = Blueprint('routes', __name__)
from app.db import db
from app import oauth
from app.story_service import continue_story_service, rewrite_story_service

# Google OAuth 回调处理
@routes_bp.route('/auth/google')
def auth_google():
    redirect_uri = url_for('routes.auth_callback', _external=True)
    import secrets
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@routes_bp.route('/auth/callback')
def auth_callback():
    token = oauth.google.authorize_access_token()
    nonce = session.pop('nonce', None)
    user_info = oauth.google.parse_id_token(token, nonce=nonce)
    
    # 根据从 Google 返回的用户信息处理登录或注册
    if not user_info:
        return jsonify({"error": "Failed to authenticate with Google"}), 400
    
    user_datastore = current_app.extensions['security'].datastore
    user = user_datastore.find_user(email=user_info['email'])

    # 如果用户不存在，注册新用户
    if not user:
        user = user_datastore.create_user(
            email=user_info['email'],
            username=user_info.get('name', user_info['email']),
            password=None  # Google OAuth 登录通常不需要密码
        )
        db.session.commit()

    # 登录用户
    session['user'] = {'email': user.email, 'username': user.username, 'type': 'google'}

    return redirect(url_for('routes.index'))

# Register route added here
@routes_bp.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        action = request.form['action']
        email = request.form['email']
        password = request.form['password']
        user_datastore = current_app.extensions['security'].datastore

        if action == 'register':
            import random
            import string
            username = request.form.get('username', ''.join(random.choices(string.ascii_letters + string.digits, k=8)))

            if user_datastore.find_user(email=email):
                return render_template('auth.html', error='Email already registered')
            if user_datastore.find_user(username=username):
                return render_template('auth.html', error='Username already taken')

            try:
                user_datastore.create_user(username=username, email=email, password=hash_password(password))
                db.session.commit()
                return redirect(url_for('routes.index'))
            except Exception as e:
                db.session.rollback()
                return render_template('auth.html', error=str(e))

        elif action == 'login':
            user = user_datastore.find_user(email=email)
            if user:
                if user.password == password:
                    session['user'] = {'email': user.email, 'username': user.username, 'type': 'local'}
                    return redirect(url_for('routes.index'))
                else:
                    current_app.logger.error(f"Password mismatch for user {email}")
                    return render_template('auth.html', error='Invalid password')
            else:
                current_app.logger.error(f"User not found: {email}")
                return render_template('auth.html', error='User not found')

    return render_template('auth.html')

@routes_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        user_datastore = current_app.extensions['security'].datastore
        user = user_datastore.find_user(email=session['user']['email'])

        if not user or not user.password == current_password:
            return render_template('auth.html', error='Current password is incorrect')

        if new_password != confirm_password:
            return render_template('auth.html', error='New passwords do not match')

        try:
            user.password = hash_password(new_password)
            db.session.commit()
            return redirect(url_for('routes.index'))
        except Exception as e:
            db.session.rollback()
            return render_template('auth.html', error=str(e))

    return render_template('auth.html')

@routes_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('routes.index'))

@routes_bp.route('/fix_stories', methods=['POST'])
def fix_stories():
    # 获取前4个故事
    stories = Story.query.limit(4).all()
    for story in stories:
        # 将故事分配给其他用户并设置为开放状态
        story.user_id = 2  # 假设用户ID 2是其他用户
        story.is_open = True
    db.session.commit()
    return render_template('fix_stories.html')
@routes_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    open_stories = Story.query.filter_by(is_open=True).limit(4).all()
    return render_template('recommendations.html', stories=open_stories)

@routes_bp.route('/')
def index():
    return render_template('index.html')

@routes_bp.route('/api/stories/<int:story_id>/chapters', methods=['POST'])
def add_chapter(story_id):
    logging.debug(f"Request path: {request.path}")
    data = request.get_json()
    story = Story.query.get_or_404(story_id)
    
    preferences = data.get('preferences', {})
    # 获取前面章节的历史作为context
    context = " ".join([chapter.body for chapter in story.chapters])
    preferences['context'] = context
    new_content = generate_story(preferences)

    if 'body' in new_content:
        new_chapter = Chapter(title="New Chapter", body=new_content['body'], story=story)
    else:
        return jsonify({'error': 'Chapter generation failed'}), 500
    db.session.add(new_chapter)
    db.session.commit()

    return jsonify({'story': story.id, 'title': story.title, 'body': story.body, 'chapters': [{'id': new_chapter.id, 'title': new_chapter.title, 'body': new_chapter.body} for chapter in story.chapters]}), 201

@routes_bp.route('/api/stories/new', methods=['GET', 'POST'])
def create_story():
    data = request.get_json()
    new_story = Story(title=data['title'], body=data['body'])
    db.session.add(new_story)
    db.session.commit()
    return jsonify({'id': new_story.id, 'title': new_story.title, 'body': new_story.body}), 201

@routes_bp.route('/api/stories/<int:id>', methods=['GET'])
def get_story(id):
    story = Story.query.get_or_404(id)
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200

@routes_bp.route('/api/stories/<int:id>', methods=['DELETE'])
def delete_story(id):
    story = Story.query.get_or_404(id)
    db.session.delete(story)
    db.session.commit()
    return '', 204

@routes_bp.route('/api/stories/<int:id>/continue', methods=['POST'])
def continue_story_route(id):
    data = request.get_json()
    story = Story.query.get_or_404(id)
    new_content = continue_story_service(id, data['preferences'])
    story.body += new_content['body']
    db.session.commit()
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200

@routes_bp.route('/api/stories/<int:id>/rewrite', methods=['POST'])
def rewrite_story_route(id):
    data = request.get_json()
    story = Story.query.get_or_404(id)
    new_content = rewrite_story_service(id, data['preferences'])
    story.body = new_content['body']
    db.session.commit()
    return jsonify({'id': story.id, 'title': story.title, 'body': story.body}), 200


@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    return jsonify({'id': chapter.id, 'title': chapter.title, 'body': chapter.body}), 200

@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>', methods=['DELETE'])
def delete_chapter(id, chapter_id):
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    db.session.delete(chapter)
    db.session.commit()
    return '', 204

@routes_bp.route('/api/stories/<int:id>/chapters/<int:chapter_id>/rewrite', methods=['POST'])
def rewrite_chapter(id, chapter_id):
    data = request.get_json()
    chapter = Chapter.query.filter_by(story_id=id, id=chapter_id).first_or_404()
    new_content = rewrite_chapter(id, chapter_id, data['preferences'])
    chapter.body = new_content['body']
    db.session.commit()
    return jsonify({'id': chapter.id, 'title': chapter.title, 'body': chapter.body}), 200
